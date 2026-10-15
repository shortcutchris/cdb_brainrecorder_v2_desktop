import unittest

from scripts.check_wake_candidates import score_case


class WakeCandidateScoringTests(unittest.TestCase):
    def test_one_detection_does_not_pass_two_separated_calls(self):
        result = score_case(True, 2, 1)
        self.assertTrue(result['activation_presence_passed'])
        self.assertEqual(result['expected_detections'], 2)
        self.assertFalse(result['passed'])

    def test_extra_detections_fail(self):
        self.assertFalse(score_case(True, 1, 2)['passed'])
        self.assertFalse(score_case(False, 2, 1)['passed'])

    def test_exact_counts_and_silent_negatives_pass(self):
        self.assertTrue(score_case(True, 1, 1)['passed'])
        self.assertTrue(score_case(True, 2, 2)['passed'])
        self.assertTrue(score_case(False, 2, 0)['passed'])


if __name__ == '__main__':
    unittest.main()
