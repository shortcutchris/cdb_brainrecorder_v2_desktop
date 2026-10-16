import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_first_start import module, factory

builder=module('customer_builder','scripts/prepare_customer_image.py')
audit=module('customer_audit','scripts/audit_customer_rootfs.py')

class CustomerImageTests(unittest.TestCase):
    def test_export_allowlist_excludes_customer_data_and_private_keys(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';source.mkdir()
            entries={'requirements-wake.txt':'pymicro-wakeword==2.5.0', 'services/wake_detectors.py':'# engines', 'services/remote_control.py':'# domain', 'services/remote_control_transport.py':'# outgoing', 'studio/remote-control.js':'// UI', 'studio/remote-control.css':'/* UI */', 'remote-control/connection.json':'PRIVATE', 'remote-control/receipts.sqlite3':'PRIVATE', 'web_server.py':"VERSION = '0.5.44'",'data/sessions.db':'PRIVATE','studio/welcome.html':'Hello','fleet/__init__.py':'','deploy/customer-image/network_service.py':'# network','deploy/customer-image/01-run-chroot.sh':'#!/bin/bash\n','kiosk.sh':'#!/bin/bash\n','scripts/audit_customer_rootfs.py':'# audit','credential.json':'PRIVATE','release-private.pem':'PRIVATE'}
            for name,value in entries.items():
                path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value)
            key=root/'public.pem';key.write_bytes(Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
            def git(args,**kwargs):
                if 'status' in args:return b''
                return ('\0'.join(entries)+'\0').encode() if 'ls-files' in args else b'abc123\n'
            with patch.object(builder,'SOURCE',source),patch.object(builder.subprocess,'check_output',side_effect=git):
                result=builder.prepare(root/'kit',key)
            self.assertIn('requirements-wake.txt',result['source_files'])
            self.assertIn('services/wake_detectors.py',result['source_files'])
            self.assertNotIn('data/sessions.db',result['source_files'])
            for name in ('services/remote_control.py','services/remote_control_transport.py','studio/remote-control.js','studio/remote-control.css'):
                self.assertIn(name,result['source_files'])
            self.assertNotIn('remote-control/connection.json',result['source_files'])
            self.assertNotIn('remote-control/receipts.sqlite3',result['source_files'])
            self.assertNotIn('credential.json',result['source_files'])
            self.assertNotIn('release-private.pem',result['source_files'])
            self.assertEqual(result['status'],'prepared-not-boot-certified')
            self.assertIn('--docker', (root/'kit/build.sh').read_text())
            with patch.object(builder.subprocess,'check_output',return_value=b' M web_server.py'):
                with self.assertRaisesRegex(ValueError,'Commit tracked changes'):
                    builder.prepare(root/'dirty-kit',key)
            with self.assertRaises(ValueError):builder.prepare(root/'kit',key)
            with self.assertRaises(ValueError):builder.prepare(root/'other',key,'http://example.com')

    def test_rootfs_audit_fails_closed_on_customer_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'etc').mkdir();(root/'etc/cdb-factory-image.json').write_text('{}')
            (root/'etc/shadow').write_text('root:!:0::::::\ncdb:!:0::::::\n');(root/'etc/machine-id').write_text('')
            self.assertTrue(audit.audit(root)['clean'])
            wifi=root/'etc/NetworkManager/system-connections/customer.nmconnection';wifi.parent.mkdir(parents=True);wifi.write_text('secret')
            with self.assertRaises(ValueError):audit.audit(root)
            wifi.unlink();(root/'etc/machine-id').write_text('shared-identity')
            with self.assertRaises(ValueError):audit.audit(root)

    def test_fresh_profile_resume_does_not_overwrite_state(self):
        from fleet.common import read,save
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source';(source/'fleet').mkdir(parents=True)
            (source/'fleet/__init__.py').write_text('');key=root/'public.pem';key.write_text('public test key')
            home=root/'home';home.mkdir()
            self.assertTrue(factory.initialize(home,source,key,'https://example.com','runtime','0.5.44'))
            state=home/'.local/share/cdb-recorder-local/first-start.json'
            display=home/'.config/kanshi/config'
            self.assertIn('output DSI-2 transform 90',display.read_text())
            display.write_text('customer display profile')
            self.assertTrue(read(state)['required']);save(state,{'step':'pair','required':True})
            factory.initialize(home,source,key,'https://example.com','runtime','0.5.44')
            self.assertEqual(read(state)['step'],'pair')
            self.assertEqual(display.read_text(),'customer display profile')
            (home/'.cdb-factory-ready').touch()
            self.assertFalse(factory.initialize(home,source,key,'https://example.com','runtime','0.5.44'))
