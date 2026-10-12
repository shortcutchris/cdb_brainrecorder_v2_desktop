import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from services.cdb_integration import CdbService,CdbBackend,CdbFailure,DEFAULT

CLIENT='11111111-1111-1111-1111-111111111111'
AREA='22222222-2222-2222-2222-222222222222'
DOC='33333333-3333-3333-3333-333333333333'
RECORDING='44444444-4444-4444-4444-444444444444'
class Transport:
    def __init__(self):self.sent=[];self.identity={'user_id':'user1','client_id':CLIENT,'display_name':'Testperson','is_active':True};self.fail_write=False;self.wrong_status=False
    def request(self,url,body=None,token=None,form=False):
        self.sent.append((url,body))
        if url.endswith('/auth/me'):return self.identity
        if url.endswith('/token'):return {'access_token':'synthetic-new','refresh_token':'synthetic-refresh','expires_in':3600,'token_type':'Bearer'}
        if '/knowledge-areas?' in url:return {'knowledge_areas':[{'id':AREA,'name':'synthetic','client_id':CLIENT,'is_global':False,'is_active':True}]}
        if url.endswith('/documents/ingest'):
            if self.fail_write:raise CdbFailure('lost response')
            return {'document_id':DOC,'job_id':'job1','status':'processing'}
        if url.endswith('/jobs/job1'):return {'document_id':DOC if not self.wrong_status else RECORDING,'job_id':'job1','status':'completed'}
        if url.endswith('/structure-text'):return {'content':'Testprotokoll','stop_reason':'stop'}
        if url.endswith('/transcription-jobs'):return {'recording_id':RECORDING,'job_id':'asr1','status':'queued'}
        if url.endswith('/transcription-jobs/asr1'):return {'recording_id':RECORDING,'job_id':'asr1','status':'completed','result':{'text':'Testtranskript'}}
        raise AssertionError(url)
class CdbTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.transport=Transport();self.c=CdbService(self.root,self.transport)
        self.c.save_token({'access_token':'synthetic','refresh_token':'synthetic-refresh','expires_in':3600,'token_type':'Bearer'},DEFAULT)
        self.row={'id':1,'title':'Synthetic meeting','transcription_status':'completed','notes':'Test','transcript_text':'Hello','summary_text':'Summary'}
    def tearDown(self):self.c.close();self.tmp.cleanup()
    def test_tokens_never_in_public_state_and_private_permissions(self):
        text=json.dumps(self.c.public());self.assertNotIn('synthetic-refresh',text);self.assertNotIn('"token"',text)
        self.assertEqual(os.stat(self.c.root/'session.json').st_mode&0o777,0o600)
    def test_selection_snapshot_retains_provider_and_account(self):
        self.c.configure({'transcription':'cdb'});snap=self.c.snapshot();self.c.configure({'transcription':'local'})
        self.assertEqual(snap['transcription'],'cdb');self.assertEqual(snap['binding']['user_id'],'user1')
        self.c.logout()
        with self.assertRaises(CdbFailure):self.c.session(snap['binding'])
    def test_refresh_checks_identity_before_replacing_credentials(self):
        s=self.c.read('session.json',{});s['expires']=0;self.c.write('session.json',s)
        self.transport.identity['user_id']='someone-else'
        with self.assertRaises(CdbFailure):self.c.session()
        self.assertEqual(self.c.read('session.json',{})['identity']['user_id'],'user1')
    def test_offline_local_snapshot_and_cloud_requires_login(self):
        self.c.logout();self.assertEqual(self.c.snapshot()['summary'],'local')
        with self.assertRaises(CdbFailure):self.c.configure({'summary':'cdb'})
        self.assertEqual(self.c.config()['summary'],'local')
    def test_untrusted_server_and_invalid_selection_rejected(self):
        for changes in ({'server':'https://evil.example'},{'summary':'automatic'},{'client_id':'bad'}):
            with self.assertRaises(CdbFailure):self.c.configure(changes)
    def test_text_publication_receipt_processing_and_deduplication(self):
        first=self.c.enqueue(self.row,AREA);self.assertEqual(first,self.c.enqueue(self.row,AREA));self.c.publication_once()
        self.assertEqual(self.c.public()['publications'][0]['state'],'completed')
        writes=[b for u,b in self.transport.sent if u.endswith('/ingest')];self.assertEqual(len(writes),1);self.assertFalse(writes[0]['auto_verify_tl1']);self.assertEqual(writes[0]['origin'],'ai_generated')
    def test_response_loss_never_repeats_ingest(self):
        self.c.enqueue(self.row,AREA);self.transport.fail_write=True;self.c.publication_once();self.c.publication_once()
        self.assertEqual(self.c.public()['publications'][0]['state'],'uncertain')
        self.assertEqual(sum(u.endswith('/ingest') for u,b in self.transport.sent),1)
    def test_processing_id_mismatch_not_success(self):
        self.c.enqueue(self.row,AREA);self.transport.wrong_status=True;self.c.publication_once()
        self.assertEqual(self.c.public()['publications'][0]['state'],'accepted');self.assertTrue(self.c.public()['publications'][0]['error'])
    def test_account_switch_prevents_queued_write(self):
        self.c.enqueue(self.row,AREA);s=self.c.read('session.json',{});s['identity']['user_id']='other';self.c.write('session.json',s);self.c.publication_once()
        self.assertFalse(any(u.endswith('/ingest') for u,b in self.transport.sent))
    def test_restart_keeps_receipt_and_does_not_repeat_write(self):
        self.c.enqueue(self.row,AREA);self.transport.wrong_status=True;self.c.publication_once()
        restarted=CdbService(self.root,self.transport);self.transport.wrong_status=False;restarted.publication_once()
        self.assertEqual(restarted.public()['publications'][0]['state'],'completed');self.assertEqual(sum(u.endswith('/ingest') for u,b in self.transport.sent),1)
    def test_active_meeting_cannot_be_sent_and_invalid_area_rejected(self):
        with self.assertRaises(CdbFailure):self.c.enqueue(self.row|{'transcription_status':'recording'},AREA)
        with self.assertRaises(CdbFailure):self.c.enqueue(self.row,DOC)
    def test_resume_server_asr_polls_existing_job_without_upload(self):
        folder=self.root/'meeting';folder.mkdir();(folder/'cdb-asr.json').write_text(json.dumps({'recording_id':RECORDING,'job_id':'asr1'}))
        binding={'server':DEFAULT['server'],'user_id':'user1','client_id':CLIENT}
        result=CdbBackend(self.c).remote_transcribe(folder,{'binding':binding})
        self.assertEqual(result,'Testtranskript');self.assertEqual(sum('transcription-jobs/' in u for u,b in self.transport.sent),1)
    def test_unknown_old_job_defaults_local(self):
        self.assertEqual(CdbBackend(self.c).route(self.root,{})['transcription'],'local')
    def test_destination_is_durable_and_hidden_after_logout(self):
        self.c.select_area(AREA);self.assertEqual(CdbService(self.root,self.transport).public()['destination']['id'],AREA)
        self.c.logout();self.assertIsNone(self.c.public()['destination'])
    def test_live_microsoft_verification_url_and_cancel(self):
        original=self.transport.request
        def request(url,*args,**kwargs):
            if url.endswith('/devicecode'):return {'device_code':'synthetic-device','user_code':'TEST-CODE','verification_uri':'https://login.microsoft.com/device','expires_in':900,'interval':5}
            return original(url,*args,**kwargs)
        self.transport.request=request
        result=self.c.start_login();self.assertEqual(result['login']['state'],'pending');self.assertNotIn('synthetic-device',json.dumps(result))
        self.c.logout();self.assertEqual(self.c.public()['login']['state'],'idle')
    def test_arbitrary_verification_destination_is_rejected(self):
        self.transport.request=lambda *a,**k:{'device_code':'synthetic','user_code':'TEST','verification_uri':'https://evil.example','expires_in':900}
        with self.assertRaises(CdbFailure):self.c.start_login()
    def test_model_test_always_local(self):
        (self.root/'cdb-request.json').write_text(json.dumps({'transcription':'cdb','summary':'cdb'}))
        self.assertEqual(CdbBackend(self.c).route(self.root,{'model_test':True})['summary'],'local')
if __name__=='__main__':unittest.main()
