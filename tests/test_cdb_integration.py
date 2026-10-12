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
    def test_automatic_summary_uses_meeting_rules_and_custom_task_is_preserved(self):
        from unittest.mock import Mock
        from settings import MEETING_PROMPT
        backend=CdbBackend(self.c);backend.store=Mock();backend.store.list.return_value=[]
        backend.local=Mock();backend.local.generate.return_value='Protokoll'
        config={}
        self.assertEqual(backend.generate('Test',config),'Protokoll')
        self.assertEqual(backend.local.generate.call_args.args[1]['prompt'],MEETING_PROMPT)
        custom={'prompt':'Eigene Aufgaben'}
        backend.generate('Test',custom,merge=True)
        self.assertEqual(custom['prompt'],'Eigene Aufgaben')
        self.assertTrue(backend.local.generate.call_args.args[2])

    def summary_backend(self):
        from unittest.mock import Mock
        b=CdbBackend(self.c);b.store=Mock();b.store.list.return_value=[{'id':'test','state':'summarizing'}]
        b.route=Mock(return_value={'summary':'cdb','binding':{}})
        return b

    def test_truncated_cdb_summary_retries_without_returning_partial_text(self):
        from unittest.mock import patch
        b=self.summary_backend()
        with patch.object(self.c,'call',side_effect=[{'content':'','stop_reason':'length'},{'content':'Complete','stop_reason':'stop'}]) as call:
            self.assertEqual(b.generate('Source',{'prompt':'Tasks'}),'Complete')
            self.assertEqual([x.args[1]['max_tokens'] for x in call.call_args_list],[4000,8000])
            self.assertTrue(all(x.args[1]['text']=='Source' for x in call.call_args_list))
            self.assertIn('Tasks',call.call_args.args[1]['instructions'])

    def test_repeated_truncation_and_empty_summary_fail_closed(self):
        from unittest.mock import patch
        b=self.summary_backend()
        with patch.object(self.c,'call',return_value={'content':'PARTIAL','stop_reason':'max_tokens'}) as call:
            with self.assertRaisesRegex(CdbFailure,'Ausgabelimit'):b.generate('Source',{})
            self.assertEqual(call.call_count,2)
        with patch.object(self.c,'call',return_value={'content':'','stop_reason':'stop'}) as call:
            with self.assertRaisesRegex(CdbFailure,'leer'):b.generate('Source',{})
            self.assertEqual(call.call_count,1)

    def test_output_token_limit_alias_also_retries(self):
        from unittest.mock import patch
        b=self.summary_backend()
        with patch.object(self.c,'call',side_effect=[{'content':'PARTIAL','stop_reason':'max_output_tokens'},{'content':'Done','stop_reason':'stop'}]):
            self.assertEqual(b.generate('Source',{}),'Done')

    def test_filtered_content_cannot_become_summary(self):
        from unittest.mock import patch
        b=self.summary_backend()
        with patch.object(self.c,'call',return_value={'content':'Partial content','stop_reason':'content_filter'}) as call:
            with self.assertRaisesRegex(CdbFailure,'blockiert'):b.generate('Source',{})
            self.assertEqual(call.call_count,1)

    def test_cdb_stream_accepts_only_terminal_result_after_keepalives(self):
        import io
        from services.cdb_integration import structure_stream
        stream=io.BytesIO(b': keepalive\n\nevent: progress\ndata: {"part":1}\n\nevent: result\ndata: {"content":"Done",\ndata: "stop_reason":"completed"}\n\n')
        self.assertEqual(structure_stream(stream),{'content':'Done','stop_reason':'completed'})

    def test_cdb_stream_disconnect_error_and_invalid_result_fail_closed(self):
        import io
        from services.cdb_integration import structure_stream
        for data in [b': keepalive\n\n',b'event: error\ndata: {"message":"remote details"}\n\n',b'event: result\ndata: []\n\n']:
            with self.assertRaises(CdbFailure):structure_stream(io.BytesIO(data))

    def test_unknown_or_failed_completion_cannot_become_summary(self):
        from unittest.mock import patch
        b=self.summary_backend()
        for reason in ('failed','unknown',None):
            with patch.object(self.c,'call',return_value={'content':'Partial content','stop_reason':reason}):
                with self.assertRaisesRegex(CdbFailure,'bestätigt'):b.generate('Source',{})

    def test_oversized_summary_is_reduced_not_truncated(self):
        from unittest.mock import patch
        b=self.summary_backend();long='Original task. '*300
        with patch.object(self.c,'call',side_effect=[{'content':long,'stop_reason':'completed'},{'content':'Compact tasks','stop_reason':'completed'}]) as call:
            self.assertEqual(b.generate('Source',{'chunk_chars':6000}),'Compact tasks')
            self.assertEqual(call.call_args_list[1].args[1]['text'],long.strip())
        with patch.object(self.c,'call',return_value={'content':long,'stop_reason':'completed'}):
            with self.assertRaisesRegex(CdbFailure,'Teilprotokoll zu lang'):b.generate('Source',{'chunk_chars':6000})

    def test_bounded_cdb_outputs_converge_for_hour_sized_transcript(self):
        import threading
        from unittest.mock import patch
        from meeting_recorder.processing import summarize
        b=self.summary_backend();progress=[]
        with patch.object(self.c,'call',return_value={'content':'Task\n'*587,'stop_reason':'completed'}) as call:
            result=summarize('Source data\n'*5000,{'chunk_chars':6000},b,threading.Event(),progress.append)
            self.assertTrue(result.startswith('Task'))
            self.assertLess(len(result)*2+5,6000)
            self.assertLess(call.call_count,40)
            self.assertTrue(any('Stufe' in p for p in progress))

    def test_standard_cdb_summary_uses_grounded_extraction_in_real_job_folder(self):
        from unittest.mock import patch
        from settings import TASK_PROMPT
        b=self.summary_backend();folder=self.root/'meeting';folder.mkdir()
        source='AA erstellt die Prüfliste bis Mittwoch.';(folder/'transcript.txt').write_text(source)
        b.store.folder.return_value=folder
        result={'tasks':[{'quote':source,'action':'erstellt die Prüfliste','owner':'AA','due':'Mittwoch'}],'events':[],'decisions':[],'open_points':[]}
        config={'chunk_chars':6000,'prompt':TASK_PROMPT}
        with patch.object(self.c,'call',return_value={'content':json.dumps(result),'stop_reason':'completed'}) as call:
            summary=b.generate(source,config)
            self.assertIn('Name unklar (Transkript: „AA“)',summary)
            self.assertNotIn('Anna:',summary)
            self.assertEqual(config['summary_model'],'cdb/agent-structure-text')
            self.assertEqual(call.call_args.args[1]['max_tokens'],8000)

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
    def test_changing_default_does_not_retarget_existing_publication(self):
        other={'id':DOC,'name':'other','label':'Other','client_id':CLIENT,'global':False}
        first={'id':AREA,'name':'synthetic','label':'Synthetic','client_id':CLIENT,'global':False}
        with patch.object(self.c,'areas',return_value=[first,other]):
            self.c.select_area(AREA)
            publication=self.c.enqueue(self.row,AREA)
            self.c.select_area(DOC)
            self.assertEqual(self.c.public()['destination']['id'],DOC)
            with self.c.db() as db:
                payload=json.loads(db.execute('SELECT payload FROM publications WHERE id=?',(publication['id'],)).fetchone()[0])
            self.assertEqual(payload['area']['id'],AREA)
            self.c.publication_once()
        writes=[body for url,body in self.transport.sent if url.endswith('/ingest')]
        self.assertEqual(writes[0]['knowledge_area'],'synthetic')

    def test_arbitrary_verification_destination_is_rejected(self):
        self.transport.request=lambda *a,**k:{'device_code':'synthetic','user_code':'TEST','verification_uri':'https://evil.example','expires_in':900}
        with self.assertRaises(CdbFailure):self.c.start_login()
    def test_model_test_always_local(self):
        (self.root/'cdb-request.json').write_text(json.dumps({'transcription':'cdb','summary':'cdb'}))
        self.assertEqual(CdbBackend(self.c).route(self.root,{'model_test':True})['summary'],'local')
if __name__=='__main__':unittest.main()


class HttpIdentificationTests(unittest.TestCase):
    def test_json_requests_identify_application(self):
        from services.cdb_integration import Transport as HttpTransport, USER_AGENT
        from unittest.mock import MagicMock
        opener=MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value=b'{}'
        with patch('services.cdb_integration.urllib.request.build_opener',return_value=opener):
            HttpTransport().request('https://staging.cdbos.de/api/v1/auth/me',token='synthetic')
        request=opener.open.call_args.args[0]
        self.assertEqual(request.get_header('User-agent'),USER_AGENT)
        self.assertEqual(request.get_header('Authorization'),'Bearer synthetic')

    def test_audio_upload_identifies_application(self):
        from services.cdb_integration import Transport as HttpTransport, USER_AGENT
        from unittest.mock import MagicMock
        import threading
        connection=MagicMock();connection.getresponse.return_value.status=201
        connection.getresponse.return_value.read.return_value=b'{}'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.ogg';path.write_bytes(b'synthetic audio')
            with patch('services.cdb_integration.http.client.HTTPSConnection',return_value=connection):
                HttpTransport().upload(DEFAULT['server'],'synthetic',path,CLIENT,'synthetic.ogg',threading.Event())
        connection.putheader.assert_any_call('User-Agent',USER_AGENT)
