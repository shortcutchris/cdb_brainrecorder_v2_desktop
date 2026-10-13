import json
import threading
import unittest
import urllib.request
import urllib.error
from services.remote_display import DisplayHub


class FakeLive:
    def __init__(self):
        self.history = [{'role': 'assistant', 'text': f'Beitrag {i} <script>unsafe</script>'} for i in range(305)]
    def display_snapshot(self, binding):
        return {'session':'synthetic', 'state':'listening', 'areas':['Testbereich'], 'history':self.history[:]}


class DisplayTests(unittest.TestCase):
    def setUp(self):
        self.now=1000.;self.account={'binding':{'server':'test','user_id':'one','client_id':'tenant'},'generation':1}
        self.live=FakeLive();self.hub=DisplayHub(self.live,lambda:self.account,('127.0.0.1',0),clock=lambda:self.now)
        self.hub.enable();self.base='http://127.0.0.1:'+str(self.hub.server.server_port)
    def tearDown(self):self.hub.close()
    def req(self,path,body=None,cookie='',headers=None):
        request=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers={'Cookie':cookie,'X-Display-Request':'1','Content-Type':'application/json'}|(headers or {}))
        try:r=urllib.request.urlopen(request,timeout=3)
        except urllib.error.HTTPError as error:r=error
        with r:return r.status,r.read(),r.headers
    def paired(self):
        token,row=self.hub.begin('Test');self.hub.pair(row['code']);return token
    def test_pairing_requires_code_and_cookie_and_only_exposes_chat(self):
        status,body,headers=self.req('/api/begin',{'name':'Testbrowser'})
        self.assertEqual(status,200);data=json.loads(body);cookie=headers['Set-Cookie'].split(';')[0]
        self.assertRegex(data['code'],r'^\d{6}$');self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        self.assertEqual(self.req('/api/display')[0],401)
        self.assertNotIn('history',json.loads(self.req('/api/display',cookie=cookie)[1]))
        with self.assertRaises(ValueError):self.hub.pair('000000')
        self.hub.pair(data['code']);result=json.loads(self.req('/api/display',cookie=cookie)[1])
        self.assertTrue(result['paired']);self.assertEqual(result['total'],305)
        self.assertNotIn('binding',result);self.assertNotIn('token',result)
        for path in ('/api/state','/api/record/start','/api/cdb/config','/../web_server.py'):
            self.assertEqual(self.req(path,cookie=cookie)[0],404)
        self.assertEqual(self.req('/api/record/start',{},cookie)[0],404)
    def test_complete_history_pagination_revision_and_new_turn(self):
        token=self.paired();first=self.hub.pulse(token);all_rows=[];offset=0
        while True:
            data=self.hub.pulse(token,offset);all_rows+=data['history'];offset+=len(data['history'])
            if not data['more']:break
        self.assertEqual(all_rows,self.live.history)
        unchanged=self.hub.pulse(token,revision=first['revision']);self.assertTrue(unchanged['unchanged']);self.assertNotIn('history',unchanged)
        self.live.history[0]['text']='Aktualisiert'
        self.assertNotEqual(self.hub.pulse(token)['revision'],first['revision'])
    def test_heartbeat_reconnect_expiry_and_account_switch(self):
        token=self.paired();self.assertTrue(self.hub.status()['connected'])
        self.now+=16;self.assertFalse(self.hub.status()['connected']);self.assertTrue(self.hub.status()['paired'])
        self.hub.pulse(token);self.assertTrue(self.hub.status()['connected'])
        self.account={**self.account,'generation':2}
        with self.assertRaises(PermissionError):self.hub.pulse(token)
        token=self.paired();self.now+=601
        with self.assertRaises(PermissionError):self.hub.pulse(token)
    def test_pending_expiry_rate_limits_and_single_receiver(self):
        token,data=self.hub.begin('First');self.now+=121
        with self.assertRaises(ValueError):self.hub.pair(data['code'])
        with self.assertRaises(PermissionError):self.hub.pulse(token)
        token=self.paired();other,data=self.hub.begin('Second');self.hub.pair(data['code'])
        with self.assertRaises(PermissionError):self.hub.pulse(token)
        self.hub.revoke()
        with self.assertRaises(PermissionError):self.hub.pulse(other)
        for _ in range(5):
            with self.assertRaises(ValueError):self.hub.pair('000000')
        _,data=self.hub.begin('Third')
        with self.assertRaisesRegex(ValueError,'Viele|viele'):self.hub.pair(data['code'])
    def test_origin_host_csrf_and_no_receiver_control(self):
        for headers in ({'Origin':'http://evil.example'},{'Host':'evil.example'},{'X-Display-Request':''}):
            self.assertEqual(self.req('/api/begin',{},headers=headers)[0],403)
        self.assertEqual(self.req('/api/display',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.req('/api/begin',{'name':'x'*2000})[0],413)
        self.assertIn("frame-ancestors 'none'",self.req('/')[2]['Content-Security-Policy'])
        self.assertEqual(self.req('/api/pair',{'code':'123456'})[0],404)
    def test_account_change_during_snapshot_never_returns_data(self):
        token=self.paired();original=self.live.display_snapshot
        def snapshot(binding):
            self.account=None
            return original(binding)
        self.live.display_snapshot=snapshot
        with self.assertRaises(PermissionError):self.hub.pulse(token)
    def test_revoke_leave_and_restart_require_new_pairing(self):
        token=self.paired();self.hub.leave(token)
        with self.assertRaises(PermissionError):self.hub.pulse(token)
        token=self.paired();self.hub.close();self.hub.enable()
        with self.assertRaises(PermissionError):self.hub.pulse(token)

if __name__=='__main__':unittest.main()
