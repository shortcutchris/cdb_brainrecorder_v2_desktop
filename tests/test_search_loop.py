"""Exercise the real loop scheduler and process cleanup, with silent output sinks."""
import sys
import time
import unittest
from array import array
from services.live_audio import NativeLiveAudio


class SearchLoopTests(unittest.TestCase):
    def setUp(self):
        self.audio = NativeLiveAudio({}, capture_command=['unused'], playback_command=[
            sys.executable, '-c', 'import sys; sys.stdin.buffer.read()'])

    def tearDown(self):
        self.audio.close()
        self.assertEqual(self.audio.stats()['processes_alive'], 0)
        self.assertFalse(self.audio.thread.is_alive())
        self.assertFalse(self.audio.feedback()['search_audio']['playing'])

    def wait(self, predicate, seconds=2):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if predicate(): return
            time.sleep(.01)
        self.assertTrue(predicate())

    def test_feedback_reports_written_audio_including_tail_not_just_search(self):
        a=self.audio
        self.assertFalse(a.feedback()['search_audio']['playing'])
        a.set_search_sound(False)
        a.update_search('web','visual','started')
        time.sleep(.1)
        self.assertFalse(a.feedback()['search_audio']['playing'])
        a.set_search_sound(True)
        self.wait(lambda:a.feedback()['search_audio']['playing'])
        a.update_search('web','visual','done')
        self.assertEqual(a.feedback()['search']['web'],0)
        self.assertTrue(a.feedback()['search_audio']['playing'])
        self.wait(lambda:a.stats()['processes_alive']==0,3)
        self.assertFalse(a.feedback()['search_audio']['playing'])
        a.update_search('web','next','started')
        self.wait(lambda:a.feedback()['search_audio']['playing'])
        a.set_search_sound(False)
        self.assertFalse(a.feedback()['search_audio']['playing'])

    def test_continuous_loop_parallel_searches_and_terminal_events(self):
        a = self.audio
        a.update_search('brain', 'a', 'started')
        a.update_search('web', 'b', 'started')
        a.update_search('web', 'b', 'started')
        self.wait(lambda: a.search_loop_blocks > 155, 4)
        self.assertEqual(a.search_tones, 1)
        self.assertEqual(a.stats()['processes_alive'], 1)
        a.update_search('brain', 'a', 'done')
        before = a.search_loop_blocks
        self.wait(lambda: a.search_loop_blocks > before + 3)
        a.update_search('web', 'b', 'failed')
        self.wait(lambda: a.stats()['processes_alive'] == 0)
        stopped = a.search_loop_blocks
        a.update_search('web', 'b', 'started')  # late replay cannot restart
        time.sleep(.15)
        self.assertEqual(a.search_loop_blocks, stopped)

    def test_human_speech_interrupts_and_then_resumes_without_muting_capture(self):
        a=self.audio
        a.update_search('web','a','started')
        self.wait(lambda:a.search_loop_blocks>5)
        before=a.search_tones
        a.note_user_speech()
        self.wait(lambda:a.stats()['processes_alive']==0)
        self.assertFalse(a.gate.snapshot()[1])
        self.wait(lambda:a.search_tones>before)

    def test_short_search_finishes_a_minimum_phrase(self):
        a=self.audio
        a.update_search('web','a','started')
        self.wait(lambda:a.search_loop_blocks>3)
        a.update_search('web','a','done')
        self.wait(lambda:a.stats()['processes_alive']==0,3)
        self.assertGreaterEqual(a.search_loop_blocks,89)
        self.assertEqual(a.search_tones,1)

    def test_answer_onset_ducks_but_does_not_cut_the_minimum_phrase(self):
        import threading
        a=self.audio
        a.update_search('web','a','started')
        self.wait(lambda:a.search_loop_blocks>3)
        def answer():
            for _ in range(110):
                a.output_meter.feed(array('h',[8192]*320).tobytes());time.sleep(.02)
        thread=threading.Thread(target=answer);thread.start()
        try:
            self.wait(lambda:a.stats()['processes_alive']==0,3)
            self.assertGreaterEqual(a.search_loop_blocks,89)
            self.assertEqual(a.search_tones,1)
        finally:thread.join()
        self.wait(lambda:a.search_tones>1)

    def test_followup_tool_inside_grace_keeps_one_player(self):
        a=self.audio
        a.update_search('web','a','started')
        self.wait(lambda:a.search_loop_blocks>90,3)
        a.update_search('web','a','done');time.sleep(.2)
        a.update_search('brain','b','started');time.sleep(.3)
        self.assertEqual(a.search_tones,1)
        self.assertEqual(a.search_loop_pauses,0)

    def test_disabled_start_reenable_and_end_while_speech_paused(self):
        a = self.audio
        a.set_search_sound(False)
        a.update_search('brain', 'a', 'started')
        time.sleep(.1)
        self.assertEqual(a.search_loop_blocks, 0)
        a.set_search_sound(True)
        self.wait(lambda: a.search_loop_blocks > 2)
        a.set_search_sound(False)
        self.wait(lambda: a.stats()['processes_alive'] == 0)
        a.input_meter.feed(array('h', [8192] * 320).tobytes())
        a.set_search_sound(True)
        a.update_search('brain', 'a', 'done')
        count = a.search_tones
        time.sleep(.7)
        self.assertEqual(a.search_tones, count)
        # A subsequent search still works after the previous one ended.
        a.update_search('brain', 'b', 'started')
        self.wait(lambda: a.search_tones > count)

    def test_expiry_stops_and_optional_playback_failure_does_not_fail_session(self):
        a = self.audio
        now = [100.0]
        a.searches.clock = lambda: now[0]
        a.update_search('web', 'a', 'started')
        self.wait(lambda: a.search_loop_blocks > 2)
        now[0] += 66
        self.wait(lambda: a.stats()['processes_alive'] == 0)
        a.playback_command = ['/nonexistent/search-loop-player']
        a.update_search('web', 'b', 'started')
        self.wait(lambda: a.cue_task.done())
        self.assertFalse(a.failure_sent)
        self.assertFalse(a.feedback()['search_audio']['playing'])


if __name__ == '__main__':
    unittest.main()
