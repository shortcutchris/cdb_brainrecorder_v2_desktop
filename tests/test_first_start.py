import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from fleet.common import save, read
from services.first_start import FirstStart

ROOT = Path(__file__).resolve().parents[1]

def module(name, path):
    spec=importlib.util.spec_from_file_location(name, ROOT/path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

network = module('factory_network', 'deploy/customer-image/network_service.py')
factory = module('factory_initialize', 'deploy/customer-image/initialize.py')


class FirstStartTests(unittest.TestCase):
    def test_existing_installation_is_not_onboarded_or_modified(self):
        with tempfile.TemporaryDirectory() as root:
            before=list(Path(root).iterdir());service=FirstStart(root)
            self.assertFalse(service.public({})['required'])
            self.assertEqual(list(Path(root).iterdir()),before)

    def test_factory_progress_survives_restart_and_requires_pairing_or_explicit_offline(self):
        with tempfile.TemporaryDirectory() as root:
            save(Path(root)/'first-start.json',{'required':True,'step':'welcome'})
            service=FirstStart(root);service.advance('pair',{})
            self.assertEqual(FirstStart(root).public({})['step'],'pair')
            with self.assertRaises(ValueError):service.advance('done',{})
            with self.assertRaises(ValueError):service.advance('done',{},'true')
            service.advance('done',{},True)
            self.assertFalse(FirstStart(root).public({})['required'])
            service.advance('done',{'state':'connected'})

    def test_operation_reservation_and_no_secret_in_status(self):
        with tempfile.TemporaryDirectory() as root:
            wait=threading.Event()
            def perform(body):
                wait.wait(2);raise ValueError(body['password'])
            service=FirstStart(root,perform)
            service.run_network({'action':'connect','password':'super-private'})
            with self.assertRaises(ValueError):service.run_network({'action':'status'})
            with self.assertRaises(ValueError):service.advance('done',{},True)
            wait.set();service.thread.join(3)
            self.assertFalse(service.busy)
            self.assertNotIn('super-private',json.dumps(service.public({})))
            self.assertEqual(service.result['state'],'error')

    def test_nmcli_escaping_and_keyfile_injection(self):
        self.assertEqual(network.fields(r'Office\:one:70:WPA2'),['Office:one','70','WPA2'])
        body={'ssid':'Office;ä','password':'a b\\cdef','security':'wpa2'}
        text=network.profile(body,'11111111-1111-1111-1111-111111111111')
        self.assertIn('psk=a\\sb\\\\cdef',text)
        self.assertNotIn('ssid=Office',text)
        for changes in ({'ssid':'x\n[connection]'}, {'password':'1234567'}, {'password':'12345678\nkey=x'}, {'security':'eap'},{'ssid':'ü'*17}):
            with self.assertRaises(ValueError):network.credentials(body|changes)

    def test_scan_deduplicates_and_disallows_enterprise_and_open(self):
        with tempfile.TemporaryDirectory() as root:
            def run(args):
                if 'SSID,SIGNAL,SECURITY' in args:return 'Office\\:one:70:WPA2\nOffice\\:one:30:WPA2\nCorp:90:WPA2 802.1X\nOpen:80:--'
                if 'DEVICE,TYPE,STATE,CONNECTION' in args:return 'eth0:ethernet:connected:LAN'
                if 'CONNECTIVITY' in args:return 'full'
                return 'wlan0:wifi'
            result=network.Network(root,root,run).scan()
            self.assertEqual(len(result['networks']),3)
            self.assertEqual(sum(n['supported'] for n in result['networks']),1)
            self.assertEqual(result['devices'][0]['type'],'ethernet')

    def test_failed_password_restores_original_connection_and_removes_only_candidate(self):
        with tempfile.TemporaryDirectory() as root:
            old='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';calls=[]
            def run(args):
                calls.append(args)
                if 'DEVICE,TYPE' in args:return 'wlan0:wifi'
                if 'GENERAL.CON-UUID' in args:return old
                if args[:3]==['connection','up','uuid'] and args[3]!=old:raise ValueError('incorrect password')
                return ''
            service=network.Network(root,root,run)
            original=Path(root)/'original.nmconnection';original.write_text('unchanged')
            with self.assertRaises(ValueError):service.connect({'ssid':'Test','password':'12345678'})
            self.assertIn(['connection','up','uuid',old],calls)
            self.assertEqual(original.read_text(),'unchanged')
            self.assertFalse((Path(root)/'pending.json').exists())
            self.assertEqual(list(Path(root).glob('cdb-*.nmconnection')),[])
            self.assertNotIn('12345678',repr(calls))

    def test_success_uses_private_profile_and_commits_only_after_activation(self):
        with tempfile.TemporaryDirectory() as root:
            calls=[]
            def run(args):
                calls.append(args)
                if 'DEVICE,TYPE' in args:return 'wlan0:wifi'
                if 'GENERAL.CON-UUID' in args:return '--'
                if args[:2]==['connection','load']:
                    self.assertEqual(Path(args[2]).stat().st_mode & 0o777,0o600)
                    self.assertTrue((Path(root)/'pending.json').exists())
                if 'CONNECTIVITY' in args:return 'limited'
                return ''
            result=network.Network(root,root,run).connect({'ssid':'Test','password':'12345678'})
            self.assertEqual(result['connectivity'],'limited') # WLAN without Internet is a valid local connection.
            self.assertFalse((Path(root)/'pending.json').exists())
            self.assertLess(next(i for i,c in enumerate(calls) if c[:2]==['connection','up']),next(i for i,c in enumerate(calls) if c[:2]==['connection','modify']))

    def test_restart_recovers_interrupted_candidate(self):
        with tempfile.TemporaryDirectory() as root:
            ident='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';calls=[]
            save(Path(root)/'pending.json',{'new':ident,'previous':''})
            (Path(root)/('cdb-'+ident+'.nmconnection')).write_text('secret')
            network.Network(root,root,lambda args:calls.append(args)).recover()
            self.assertEqual(calls,[['connection','delete','uuid',ident]])
            self.assertFalse((Path(root)/'pending.json').exists())

    def test_factory_refuses_existing_profile_and_preserves_completed_image(self):
        with tempfile.TemporaryDirectory() as root:
            home=Path(root);(home/'.local/share/cdb-recorder-local').mkdir(parents=True)
            with self.assertRaises(ValueError):factory.initialize(home,ROOT,'missing','https://example.com','runtime','test')
            (home/'.cdb-factory-ready').touch()
            self.assertFalse(factory.initialize(home,ROOT,'missing','https://example.com','runtime','test'))


class NetworkBoundaryTests(unittest.TestCase):
    def test_unix_socket_protocol_and_error_redaction(self):
        import socketserver
        from services.first_start import NetworkClient
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/'control.sock')
            class FakeNetwork:
                def dispatch(self,body):
                    if body['action']=='status':return {'connectivity':'full'}
                    raise RuntimeError('private-password')
            with socketserver.UnixStreamServer(path,network.Handler) as server:
                server.network=FakeNetwork()
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    client=NetworkClient(path)
                    self.assertEqual(client({'action':'status'}),{'connectivity':'full'})
                    with self.assertRaises(ValueError) as error:client({'action':'connect'})
                    self.assertNotIn('private-password',str(error.exception))
                finally:server.shutdown();thread.join(2)

    def test_pairing_waits_and_never_exposes_code(self):
        from services.device_management import DeviceManagement
        with tempfile.TemporaryDirectory() as folder:
            service=DeviceManagement(folder)
            save(service.root/'config.json',{'server':'https://example.com'})
            service.enroll('ABCD-1234-E567')
            self.assertEqual(service.public()['state'],'pairing')
            self.assertNotIn('ABCD',json.dumps(service.public()))
            with self.assertRaises(ValueError):service.enroll('ABCD-1234-E567')

if __name__=='__main__':unittest.main()
