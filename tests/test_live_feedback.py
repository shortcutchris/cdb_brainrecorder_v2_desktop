import unittest
from array import array
from services.live_feedback import AudioEnvelope,SearchActivity,web_search_event,search_chime

class FeedbackTests(unittest.TestCase):
    def test_real_envelope_silence_staleness_and_bound(self):
        now=[100.];m=AudioEnvelope(lambda:now[0]);m.feed(bytes(640));self.assertEqual(m.public()['bars'],[0]*16)
        for _ in range(100):m.feed(array('h',[8192]*320).tobytes())
        self.assertEqual(len(m.public()['bars']),16);self.assertGreater(m.public()['bars'][-1],.9);self.assertTrue(m.public()['active'])
        now[0]+=.5;self.assertEqual(m.public()['bars'],[0]*16);self.assertFalse(m.public()['active']);m.clear();self.assertTrue(m.quiet())
    def test_search_replay_out_of_order_parallel_and_expiry(self):
        now=[100.];s=SearchActivity(lambda:now[0])
        self.assertTrue(s.update('brain','a','started'));self.assertFalse(s.update('brain','a','started'))
        s.update('web','b','started');self.assertEqual(s.public()['brain'],1);self.assertEqual(s.public()['web'],1)
        s.update('brain','a','done');self.assertFalse(s.update('brain','a','started'));s.update('web','b','failed');self.assertTrue(s.public()['failed'])
        s.update('web','done-first','done');self.assertFalse(s.update('web','done-first','started'))
        s.update('brain','c','started');now[0]+=66;self.assertEqual(s.public(),{'brain':0,'web':0,'failed':False})
        for i in range(200):s.update('brain',str(i),'done')
        self.assertEqual(len(s.calls),128)
    def test_only_actual_web_tool_events_not_thinking(self):
        for event in ({'type':'session.delegation.created'},{'type':'response.event','event':{'type':'response.created'}},{'type':'response.event','event':None}):self.assertIsNone(web_search_event(event))
        self.assertEqual(web_search_event({'type':'response.event','event':{'type':'response.web_search_call.searching','item_id':'a'}}),('a','started'))
        self.assertEqual(web_search_event({'type':'response.event','event':{'type':'response.output_item.done','item':{'type':'web_search_call','id':'a','status':'completed'}}}),('a','done'))
    def test_chime_is_short_quiet_pcm(self):
        pcm=search_chime();samples=array('h');samples.frombytes(pcm)
        self.assertEqual(len(pcm),5760);self.assertLessEqual(max(abs(x) for x in samples),900);self.assertEqual(samples[0],0)
