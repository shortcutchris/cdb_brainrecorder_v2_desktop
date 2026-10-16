import unittest
from scripts.wake_candidate_comparison import compare_windows


class PairedCandidateTests(unittest.TestCase):
    def test_models_receive_identical_complete_windows_with_fixed_tails(self):
        pcm=b''.join(bytes([i])*1600 for i in range(120))
        calls=[]
        def probe(window,binary,model):
            calls.append((window,model))
            return {'detected': model=='tiny'}
        report=compare_windows(pcm,60,'binary',{'tiny':'tiny','base':'base'},probe)
        self.assertEqual(len(calls),4)
        self.assertIs(calls[0][0],calls[1][0]);self.assertIs(calls[2][0],calls[3][0])
        self.assertEqual(calls[0][0],pcm[20*1600:76*1600])
        self.assertEqual(calls[2][0],pcm[20*1600:92*1600])
        self.assertFalse(report['production_trigger'])
        self.assertNotIn('transcript',report)
        self.assertEqual([r['audio_seconds'] for r in report['windows']],[2.8,3.6])

    def test_missing_candidate_or_context_never_pads_or_invokes_model(self):
        calls=[]
        for frame in (None,10,110):
            result=compare_windows(bytes(120*1600),frame,'binary',{'a':'a','b':'b'},lambda *a:calls.append(a))
            self.assertFalse(any('models' in row for row in result['windows']))
        self.assertEqual(calls,[])

    def test_invalid_bounds_are_rejected(self):
        for pcm,frame in [(b'',1),(bytes(1601),1),(bytes(641600),1),(bytes(1600),True),(bytes(1600),2)]:
            with self.assertRaises(ValueError):
                compare_windows(pcm,frame,'binary',{'a':'a','b':'b'})


if __name__=='__main__': unittest.main()
