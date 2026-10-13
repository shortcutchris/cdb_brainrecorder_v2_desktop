import unittest
from array import array
from services.live_feedback import AudioEnvelope,SearchInputEnvelope,SearchActivity,web_search_event,search_loop_pcm

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
    def test_loop_is_three_seconds_quiet_pcm_with_silent_seam(self):
        pcm=search_loop_pcm();samples=array('h');samples.frombytes(pcm)
        self.assertEqual(len(pcm),144000);self.assertLessEqual(max(abs(x) for x in samples),2068);self.assertEqual(samples[0],0);self.assertEqual(samples[-1],0)

    def test_bell_echo_is_not_speech_but_voice_with_bells_still_interrupts(self):
        import numpy as np
        now=[100.];meter=SearchInputEnvelope(lambda:now[0])
        def feed(voice=False):
            for index in range(30):
                t=(np.arange(320)+320*index)/16000
                x=.12*np.sin(2*np.pi*523.251*t)+.04*np.sin(2*np.pi*1444.17*t)
                if voice:
                    # Voiced speech-like harmonic content outside the cue's bands.
                    x+=sum(.03/n*np.sin(2*np.pi*173*n*t) for n in range(1,12))
                block=(x*32767).astype('<i2').tobytes()
                meter.cue_playing();meter.feed(block);now[0]+=.02
        feed()
        self.assertTrue(meter.quiet())
        self.assertGreater(max(meter.public()['bars']),.3)  # waveform remains real
        feed(True)
        self.assertFalse(meter.quiet())
        meter.clear();self.assertTrue(meter.quiet())
