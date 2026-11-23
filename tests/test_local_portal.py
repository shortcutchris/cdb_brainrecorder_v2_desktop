import hashlib
import http.client
import json
from pathlib import Path
import ssl
import sys
from concurrent.futures import ThreadPoolExecutor
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from test_studio import StudioTests
from services.local_portal import LocalPortal, certificate, qr_svg, wiring_pdf, STATIC
from fleet.releases import allowed


class PortalTests(unittest.TestCase):
    def setUp(self):
        StudioTests.setUp(self)
        self.app.ambient_stop.set(); self.app.ambient_thread.join(3)
        self.now = 100.
        self.portal = self.app.portal = LocalPortal(self.app, '0.5.94', address='127.0.0.1', help_port=0, control_port=0, clock=lambda:self.now)
        self.portal.start()
        self.portal.enable()
    sign_in_fixture = StudioTests.sign_in_fixture
    tearDown = StudioTests.tearDown
    request = StudioTests.request

    def paired(self):
        token = self.portal.begin('Test-Browser')
        self.portal.approve(self.portal.status(token)['code'])
        return token

    def command(self, token, action, status=None, ident=None):
        status = status or self.portal.status(token)
        body = {'id':ident or str(uuid.uuid4()), 'action':action, 'ticket':status['ticket']}
        return self.portal.command(token, status['csrf'], body), body

    def http(self, path, body=None, secure=False, headers=None):
        port = self.portal.control_port if secure else self.portal.help_port
        conn = http.client.HTTPSConnection('127.0.0.1',port,context=ssl._create_unverified_context(),timeout=5) if secure else http.client.HTTPConnection('127.0.0.1',port,timeout=5)
        defaults={'Content-Type':'application/json','Origin':f'https://127.0.0.1:{port}','X-Portal-Request':'1'}
        if headers: defaults.update(headers)
        conn.request('POST' if body is not None else 'GET',path,body=None if body is None else json.dumps(body),headers=defaults)
        result=conn.getresponse(); value=(result.status, result.read(), dict(result.getheaders()));conn.close();return value

    def test_help_is_offline_public_and_does_not_expose_kiosk_or_state(self):
        self.app.cdb.logout()
        for path in ('/', '/help.js', '/articles.json', '/images/ablauf.svg', '/verkabelung-r2.pdf'):
            self.assertEqual(self.http(path)[0],200,path)
        for path in ('/api/state','/api/session','/api/diagnostics','/../web_server.py','/downloads.json'):
            self.assertEqual(self.http(path)[0],404,path)
        self.assertEqual(self.http('/api/pair',{'name':'x'})[0],403)
        self.assertEqual(self.http('/',headers={'Host':'evil.example'})[0],403)
        self.assertNotIn('csrf', self.http('/api/info')[1].decode())

    def test_pairing_requires_tls_origin_and_account_and_sets_private_cookie(self):
        self.assertEqual(self.http('/api/pair',{'name':'x'},secure=True,headers={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.http('/api/pair',{'name':'x'},secure=True,headers={'X-Portal-Request':'0'})[0],403)
        status,data,headers=self.http('/api/pair',{'name':'My browser'},secure=True)
        self.assertEqual(status,200)
        self.assertFalse(json.loads(data)['paired'])
        for flag in ('Secure','HttpOnly','SameSite=Strict','Path=/'):
            self.assertIn(flag,headers['Set-Cookie'])
        self.app.cdb.logout()
        self.assertEqual(self.http('/api/pair',{'name':'x'},secure=True)[0],400)

    def test_no_status_before_approval_and_no_personal_content_after(self):
        token=self.portal.begin('Browser')
        status=self.portal.status(token)
        self.assertNotIn('snapshot',status)
        self.portal.approve(status['code'])
        status=self.portal.status(token)
        for forbidden in ('fixture-user','Test User','Transkript','csrf','token','Bestand'):
            self.assertNotIn(forbidden,json.dumps(status['snapshot']))
        self.assertEqual(status['snapshot']['version'],'0.5.94')

    def test_account_switch_logout_restart_and_expiry_revoke(self):
        token=self.paired()
        self.app.cdb.generation += 1
        with self.assertRaises(PermissionError):self.portal.status(token)
        token=self.paired();self.app.room.epoch='new-epoch'
        with self.assertRaises(PermissionError):self.portal.status(token)
        token=self.paired();self.now+=601
        with self.assertRaises(PermissionError):self.portal.status(token)
        token=self.paired();self.app.cdb.logout()
        with self.assertRaises(PermissionError):self.portal.status(token)
        self.sign_in_fixture();token=self.paired()
        other=LocalPortal(self.app,'0.5.94');other.enabled=True
        with self.assertRaises(PermissionError):other.status(token)

    def test_poll_does_not_extend_room_login_or_approval_lifetime(self):
        token=self.paired();expires=self.portal.sessions[token]['expires'];touch=self.app.room.last_touch
        self.now+=50;self.portal.status(token)
        self.assertEqual(self.portal.sessions[token]['expires'],expires)
        self.assertEqual(self.app.room.last_touch,touch)
        self.now=expires
        with self.assertRaises(PermissionError):self.portal.status(token)

    def test_pair_codes_expire_and_guesses_are_limited(self):
        token=self.portal.begin('Browser');code=self.portal.status(token)['code'];self.now+=121
        with self.assertRaises(ValueError):self.portal.approve(code)
        for _ in range(4):
            with self.assertRaises(ValueError):self.portal.approve('xxxxxx')
        with self.assertRaisesRegex(ValueError,'Minute'):self.portal.approve('123456')

    def test_commands_reject_wrong_csrf_stale_ticket_and_unknown_actions(self):
        token=self.paired();s=self.portal.status(token)
        body={'id':str(uuid.uuid4()),'action':'shutdown','ticket':s['ticket']}
        with self.assertRaises(PermissionError):self.portal.command(token,'wrong',body)
        with self.assertRaises(ValueError):self.portal.command(token,s['csrf'],body)
        s=self.portal.status(token);self.portal.revision+=1
        with self.assertRaisesRegex(ValueError,'Status'):self.command(token,'record.start',s)
        s=self.portal.status(token);self.now+=16
        with self.assertRaisesRegex(ValueError,'Status'):self.command(token,'record.start',s)

    def test_duplicate_and_conflicting_receipts_never_repeat_side_effects(self):
        token=self.paired();self.app.engine.configure({'setup_complete':True})
        s=self.portal.status(token)
        with patch.object(self.app,'action') as action:
            result,body=self.command(token,'record.start',s)
            again=self.portal.command(token,s['csrf'],body)
            self.assertTrue(result['ok']);self.assertEqual(result,again);self.assertEqual(action.call_count,1)
            with self.assertRaises(ValueError):self.portal.command(token,s['csrf'],body|{'action':'talk.start'})

    def test_shared_interlocks_and_state_change_guard(self):
        token=self.paired()
        with patch.object(self.app.management,'busy',return_value=True):
            self.assertEqual(self.portal.status(token)['snapshot']['allowed'],[])
        from services.app_activity import AppActivity
        with patch.object(self.app,'activity',return_value=AppActivity(microphone_test=True)):
            self.assertEqual(self.portal.status(token)['snapshot']['allowed'],[])
        # A local mute/pause ABA invalidates pending remote buttons too.
        self.app.engine.configure({'setup_complete':True});s=self.portal.status(token)
        with patch.object(self.app,'_action',return_value={}):self.app.action('/api/record/control',{'paused':True})
        with self.assertRaises(ValueError):self.command(token,'record.start',s)

    def test_disable_revoke_and_operator_setup_guard(self):
        token=self.paired()
        self.assertEqual(self.request('/api/portal/enable',{})[0],200)
        with patch.object(self.app.room,'require_operator',side_effect=ValueError('PIN')):
            self.assertEqual(self.request('/api/portal/disable',{})[0],400)
        self.assertEqual(self.request('/api/portal/revoke',{})[0],200)
        with self.assertRaises(PermissionError):self.portal.status(token)
        self.portal.disable()
        with self.assertRaises(ValueError):self.portal.begin('Browser')

    def test_https_capture_survives_request_exit_and_browser_disconnect(self):
        self.app.engine.configure({'setup_complete': True})
        self.app.store.claim = lambda: None
        script = "import os,time\nwhile True:\n os.write(1,bytes(3200));time.sleep(.05)"
        self.app.engine.recorder.command_factory = lambda _: [sys.executable, '-u', '-c', script]
        status, data, headers = self.http('/api/pair', {'name':'Recorder test'}, secure=True)
        self.assertEqual(status,200)
        auth={'Cookie':headers['Set-Cookie'].split(';')[0], 'X-Portal-CSRF':json.loads(data)['csrf']}
        self.portal.approve(json.loads(data)['code'])
        def send(action):
            state=json.loads(self.http('/api/session',secure=True,headers=auth)[1])
            body={'id':str(uuid.uuid4()),'action':action,'ticket':state['ticket']}
            status,data,_=self.http('/api/command',body,secure=True,headers=auth)
            self.assertEqual(status,200);self.assertTrue(json.loads(data)['ok'],data)
            return body
        start=send('record.start')
        ident=self.app.engine.recorder.status()['id']
        pcm=self.app.store.folder(ident)/'audio.pcm'
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and (not pcm.exists() or pcm.stat().st_size<3200):time.sleep(.02)
        before=pcm.stat().st_size;time.sleep(.2)
        self.assertGreater(pcm.stat().st_size,before)
        self.assertEqual(self.http('/api/command',start,secure=True,headers=auth)[0],200)
        self.assertEqual(self.app.engine.recorder.status()['id'],ident)
        send('record.pause');self.assertTrue(self.app.engine.recorder.status()['paused'])
        send('record.resume');send('record.mute');self.assertTrue(self.app.engine.recorder.status()['muted'])
        send('record.unmute')
        # Leaving the browser does not stop a recording; local controls still own it.
        self.assertEqual(self.http('/api/leave',{},secure=True,headers=auth)[0],200)
        self.assertEqual(self.app.engine.recorder.status()['id'],ident)
        self.app.action('/api/record/stop',{})
        self.assertTrue((self.app.store.folder(ident)/'audio.wav').is_file())
        self.assertEqual(self.http('/api/command',start,secure=True,headers=auth)[0],403)

    def test_two_controllers_cannot_execute_from_the_same_stale_state(self):
        self.app.engine.configure({'setup_complete':True})
        first,second=self.paired(),self.paired()
        states=[self.portal.status(first),self.portal.status(second)]
        def execute(pair):
            token,status=pair
            try:return self.command(token,'record.start',status)[0]['ok']
            except ValueError:return False
        with patch.object(self.app.engine,'start',return_value='test') as start, ThreadPoolExecutor(2) as pool:
            outcomes=list(pool.map(execute,zip((first,second),states)))
            self.assertEqual(sorted(outcomes),[False,True]);self.assertEqual(start.call_count,1)

    def test_slow_wake_cleanup_cannot_start_an_expired_request(self):
        self.app.engine.configure({'setup_complete':True});token=self.paired()
        def delay(*a,**k):self.now+=16
        with patch.object(self.app.wake,'suspend',side_effect=delay),patch.object(self.app.engine,'start') as start:
            result,_=self.command(token,'record.start')
            self.assertFalse(result['ok']);self.assertIn('abgelaufen',result['message']);start.assert_not_called()

    def test_certificate_and_keys_are_per_device_persistent_private_and_not_packaged(self):
        context,fingerprint=certificate(self.portal.folder,self.portal.hostname,self.portal.ips)
        self.assertEqual(fingerprint,self.portal.fingerprint)
        self.assertEqual((self.portal.folder/'private.pem').stat().st_mode&0o777,0o600)
        with tempfile.TemporaryDirectory() as d:
            _,other=certificate(Path(d),'other-pi',[])
            self.assertNotEqual(other,fingerprint)
        for path in ('local-portal/private.pem','local-portal/settings.json','local-portal/certificate.pem'):
            self.assertFalse(allowed(path))
        context=ssl.create_default_context(cafile=str(self.portal.folder/'certificate.pem'))
        conn=http.client.HTTPSConnection('127.0.0.1',self.portal.control_port,context=context)
        conn.request('GET','/api/info');self.assertEqual(conn.getresponse().status,200);conn.close()

    def test_help_assets_and_download_integrity_and_qr(self):
        articles=json.loads((STATIC/'articles.json').read_text())
        self.assertGreaterEqual(len(articles),15)
        ids={a['id'] for a in articles};self.assertEqual(len(ids),len(articles))
        for a in articles:
            if a.get('image'):self.assertTrue((STATIC/a['image']).is_file())
            for link in a.get('links',[]):
                if link['url'].startswith('#'):self.assertIn(link['url'][1:],ids|{'remote'})
        self.assertTrue(wiring_pdf().startswith(b'%PDF-'))
        source=json.loads((STATIC/'downloads.json').read_text())['wiring']
        self.assertEqual(hashlib.sha256(wiring_pdf()).hexdigest(),source['sha256'])
        self.assertIn(b'<svg',qr_svg('http://pi.local:8091/'))
        for path in STATIC.rglob('*'):
            if path.is_file():self.assertTrue(allowed(str(path.relative_to(STATIC.parent.parent))))

if __name__=='__main__':unittest.main()
