import base64
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile
from fleet.common import save,read
from fleet.server import Registry
from fleet.releases import Updater,verify,canonical
from services.app_activity import AppActivity
from services.device_management import DeviceManagement


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.now=1000;self.r=Registry(Path(self.temp.name)/'db',lambda:self.now)
        self.code=self.r.invitation('Raum Eins')['code'];self.d=self.r.enroll(self.code,'a'*64)
    def pulse(self,**kwargs):return self.r.pulse(self.d['token'],{'hardware':'a'*64,'status':{},**kwargs})
    def test_one_use_expiry_and_duplicate(self):
        with self.assertRaises(ValueError):self.r.enroll(self.code,'b'*64)
        code=self.r.invitation('Raum Zwei')['code']
        with self.assertRaises(ValueError):self.r.enroll(code,'a'*64)
        self.now+=601
        with self.assertRaises(ValueError):self.r.enroll(code,'b'*64)
    def test_token_clone_revocation_and_redaction(self):
        with self.assertRaises(PermissionError):self.r.pulse(self.d['token'],{'hardware':'b'*64})
        self.pulse(status={'version':'1','transcript':'secret','token':'secret','activity':'idle'})
        status=self.r.overview()['devices'][0]['status'];self.assertNotIn('token',status);self.assertNotIn('transcript',status)
        self.r.revoke(self.d['id'])
        with self.assertRaises(PermissionError):self.pulse()
    def test_commands_delivery_result_offline_and_expiry(self):
        c=self.r.command(self.d['id'],'diagnose',{})
        self.assertEqual(self.pulse()['command']['id'],c['id']);self.assertEqual(self.pulse()['command']['id'],c['id'])
        self.assertIsNone(self.pulse(result={'id':c['id'],'state':'succeeded'})['command'])
        self.r.command(self.d['id'],'reboot',{});self.now+=601
        self.assertIsNone(self.pulse()['command'])
        self.now+=101;self.assertFalse(self.r.overview()['devices'][0]['online'])
    def test_no_remote_shell_or_extra_parameters(self):
        for action,payload in [('shell',{}),('reboot',{'command':'ls'}),('update',{'release':'../../x'})]:
            with self.assertRaises(ValueError):self.r.command(self.d['id'],action,payload)
    def test_device_cannot_complete_another_devices_command(self):
        other=self.r.enroll(self.r.invitation('Other')['code'],'b'*64)
        cmd=self.r.command(other['id'],'reboot',{})
        self.pulse(result={'id':cmd['id'],'state':'succeeded'})
        self.assertEqual(self.r.overview()['commands'][0]['state'],'queued')


class UpdateTests(unittest.TestCase):
    def setUp(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.key=Ed25519PrivateKey.generate();self.pub=self.root/'public.pem'
        self.pub.write_bytes(self.key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
        self.old=self.root/'old';self.old.mkdir();(self.old/'web_server.py').write_text('old')
        (self.root/'current').symlink_to(self.old);save(self.root/'accepted.json',{'version':'old','sequence':1})
        self.restarts=0
    def restart(self):self.restarts+=1
    def bundle(self,files=None,**changes):
        files=files or {'web_server.py':b'new'};b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            for k,v in files.items():z.writestr(k,v)
        m={'format':1,'version':'new','from_versions':['old'],'sequence':2,'architecture':'aarch64','runtime':'test','schema':'unchanged','expires':time.time()+60,'sha256':hashlib.sha256(b.getvalue()).hexdigest(),'files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}|changes
        return {'manifest':m,'signature':base64.b64encode(self.key.sign(canonical(m))).decode(),'archive':base64.b64encode(b.getvalue()).decode()}
    def updater(self,health=lambda version:True):return Updater(self.root,self.pub,'test',self.restart,health,architecture='aarch64')
    def test_success_and_replay_blocked(self):
        u=self.updater();u.install(self.bundle());self.assertEqual((u.current/'web_server.py').read_text(),'new');self.assertTrue(self.old.exists())
        with self.assertRaises(ValueError):u.install(self.bundle())
        self.assertEqual(self.restarts,1)
    def test_bad_signature_and_corrupt_archive_never_restart(self):
        bundle=self.bundle();bundle['manifest']['version']='tampered'
        with self.assertRaises(Exception):self.updater().install(bundle)
        bundle=self.bundle();bundle['archive']=base64.b64encode(b'bad').decode()
        with self.assertRaises(ValueError):self.updater().install(bundle)
        self.assertEqual(self.restarts,0)
    def test_wrong_arch_runtime_migration_expired(self):
        for changes in ({'architecture':'x86_64'},{'runtime':'other'},{'schema':'migration'},{'expires':0},{'sequence':1}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.updater().install(self.bundle(**changes))
        self.assertEqual(self.restarts,0)
    def test_path_traversal_and_userdata_rejected(self):
        for path in ('../outside','/tmp/evil','data/sessions.db','data/account.json','models/x.bin','.env','services/../../outside'):
            with self.subTest(path=path),self.assertRaises(ValueError):self.updater().install(self.bundle({path:b'evil','web_server.py':b'new'}))
    def test_unhealthy_release_rolls_back(self):
        u=self.updater(lambda version:version=='old')
        with self.assertRaises(ValueError):u.install(self.bundle())
        self.assertEqual(u.current.resolve(),self.old);self.assertEqual(read(u.ledger)['version'],'old');self.assertEqual(self.restarts,2)
    def test_crash_recovery_before_and_after_commit(self):
        u=self.updater();new=self.root/'new';new.mkdir();u.link(new)
        save(u.journal,{'previous':str(self.old),'previous_version':'old','release':'candidate'})
        self.assertTrue(u.recover());self.assertEqual(u.current.resolve(),self.old)
        u.link(new);save(u.journal,{'previous':str(self.old),'previous_version':'old','release':'candidate'});save(u.ledger,{'release':'candidate'})
        u.recover();self.assertEqual(u.current.resolve(),new)
    def test_failed_rollback_keeps_recovery_journal(self):
        u=self.updater(lambda _:False)
        with self.assertRaises(ValueError):u.install(self.bundle())
        self.assertTrue(u.journal.exists());self.assertEqual(u.current.resolve(),self.old)


class MaintenanceTests(unittest.TestCase):
    def test_all_activity_capabilities_blocked(self):
        a=AppActivity(maintenance=True)
        self.assertTrue(a.occupied);self.assertFalse(a.alarm_allowed)
        self.assertTrue(all(not v['allowed'] for v in a.capabilities(setup_complete=True,brain_signed_in=True).values()))
    def test_expiring_lock_and_wrong_release_id(self):
        with tempfile.TemporaryDirectory() as folder:
            m=DeviceManagement(folder);save(m.marker,{'command':'a','expires':time.time()+10})
            m.release('b');self.assertTrue(m.busy());m.release('a');self.assertFalse(m.busy())
            save(m.marker,{'command':'a','expires':0});self.assertFalse(m.busy())
            self.assertFalse(m.authorized('bad'));self.assertTrue(m.authorized('Bearer '+read(m.auth)['token']))

if __name__=='__main__':unittest.main()

class AgentTests(unittest.TestCase):
    def setUp(self):
        from fleet.agent import Agent
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        save(self.root/'config.json',{'server':'https://example.test'})
        save(self.root/'credential.json',{'token':'private','hardware':'a'*64,'name':'Pi'})
        self.executions=[]
        self.agent=Agent(self.root,identity=lambda:'a'*64,execute=lambda c:self.executions.append(c['id']) or 'done')
        self.command={'id':'one','action':'diagnose','expires':time.time()+60,'payload':{}}
    def test_repeated_delivery_does_not_repeat_action(self):
        with patch('fleet.agent.request',return_value={'command':self.command}),patch.object(self.agent,'local',return_value={}),patch.object(self.agent,'boot',return_value='boot'):
            self.agent.tick();self.agent.tick()
        self.assertEqual(self.executions,['one']);self.assertEqual(read(self.root/'result.json')['state'],'succeeded')
    def test_hardware_clone_never_contacts_server(self):
        self.agent.identity=lambda:'b'*64
        with patch('fleet.agent.request') as network,patch.object(self.agent,'local',return_value={}):self.agent.tick()
        network.assert_not_called();self.assertEqual(read(self.root/'public.json')['state'],'hardware-changed')
    def test_expired_command_never_executes(self):
        self.command['expires']=0
        with patch('fleet.agent.request',return_value={'command':self.command}),patch.object(self.agent,'local',return_value={}):self.agent.tick()
        self.assertEqual(self.executions,[])
    def test_inflight_never_replayed_after_restart(self):
        from fleet.agent import Agent
        save(self.root/'inflight.json',self.command|{'boot':'old'})
        with patch.object(Agent,'local',return_value={}):again=Agent(self.root,identity=lambda:'a'*64)
        self.assertEqual(again.result['state'],'interrupted');self.assertFalse((self.root/'inflight.json').exists())

class HTTPTests(unittest.TestCase):
    def test_auth_origin_invitations_and_no_sensitive_inventory(self):
        import threading
        import urllib.request
        import urllib.error
        from http.server import ThreadingHTTPServer
        from fleet.server import Handler
        from fleet.common import digest,request
        with tempfile.TemporaryDirectory() as temp:
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.registry=Registry(Path(temp)/'db');server.admin_hash=digest('admin');server.origin='https://admin.test';server.attempts=[];server.rate_lock=threading.Lock();server.releases=Path(temp)/'releases';server.releases.mkdir()
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
            base='http://127.0.0.1:'+str(server.server_port)
            self.assertTrue(request(base,'/health')['ok'])
            with self.assertRaises(urllib.error.HTTPError):request(base,'/api/overview')
            r=urllib.request.Request(base+'/api/overview',headers={'Origin':'https://evil.test','Authorization':'Bearer admin'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(r)
            self.assertEqual(error.exception.code,403)
            code=request(base,'/api/invite',{'name':'HTTP device'},'admin')['code']
            d=request(base,'/api/enroll',{'code':code,'hardware':'a'*64})
            request(base,'/api/pulse',{'hardware':'a'*64,'status':{'version':'1','history':'secret'}},d['token'])
            result=request(base,'/api/overview',token='admin')
            self.assertEqual(result['devices'][0]['status'],{'version':'1'});self.assertNotIn(d['token'],json.dumps(result))
