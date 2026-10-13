import unittest
from services.app_activity import AppActivity

class ActivityTests(unittest.TestCase):
    def test_every_exclusive_activity_blocks_other_starts_and_configuration(self):
        variants=[
            {'recording':True},{'recording':True,'paused':True},{'live':'connecting'},{'live':'active'},
            {'live':'stopping'},{'live':'closing'},{'live':'listening'},{'live':'speaking'},{'live':'thinking'},{'live':'reconnecting'},{'live':'future-state','live_reserved':True},{'microphone_test':True},{'speaker_test':True},{'download':True},{'model_test':True},{'bluetooth':True}]
        for fields in variants:
            with self.subTest(fields=fields):
                a=AppActivity(**fields);c=a.capabilities(setup_complete=True,brain_signed_in=True)
                self.assertTrue(a.public()['busy']);self.assertTrue(a.reason)
                for operation in ('record','live','configure','probe','install','model_test','finish_setup'):
                    self.assertFalse(c[operation]['allowed'],operation);self.assertTrue(c[operation]['reason'])
    def test_terminal_live_states_release_resources(self):
        for state in ('idle','ended','failed'):
            a=AppActivity(live=state);self.assertFalse(a.occupied)
            c=a.capabilities(setup_complete=True,brain_signed_in=True)
            self.assertTrue(c['record']['allowed']);self.assertTrue(c['live']['allowed'])
    def test_processing_queue_does_not_block_recording_or_live(self):
        c=AppActivity(pending=True).capabilities(setup_complete=True,brain_signed_in=True)
        self.assertTrue(c['record']['allowed']);self.assertTrue(c['live']['allowed']);self.assertFalse(c['model_test']['allowed'])
    def test_prerequisites_remain_separate(self):
        c=AppActivity().capabilities(setup_complete=True,brain_signed_in=False)
        self.assertTrue(c['record']['allowed']);self.assertFalse(c['live']['allowed'])
        self.assertFalse(AppActivity().capabilities(setup_complete=True,low_disk=True)['record']['allowed'])
