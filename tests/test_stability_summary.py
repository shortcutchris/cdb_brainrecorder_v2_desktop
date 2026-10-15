import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('stability_summary', Path(__file__).parents[1] / 'scripts/summarize_pi_stability.py')
summary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary)


class StabilitySummaryTests(unittest.TestCase):
    def setUp(self):
        self.start = 1792077853
        self.end = self.start + 86400
        self.plan = {'start_epoch': self.start, 'end_epoch': self.end}
        self.status = {**self.plan, 'status': 'complete'}
        self.rows = [self.row(t) for t in range(0, 86400, 15)]
        self.events = [self.event('observer_started', 0), self.event('observation_complete', 86400)]
        self.wake()

    def at(self, offset):
        return datetime.fromtimestamp(self.start + offset, timezone.utc).isoformat()

    def row(self, offset):
        return {'at': self.at(offset), 'browser': {'rss_mb': 900, 'processes': 9, 'cpu_percent': 12},
                'activity': 'idle', 'health_ms': 10, 'version': '0.5.50', 'browser_generation': [[10, 100]]}

    def event(self, kind, offset, **fields):
        return {'type': kind, 'at': self.at(offset), **fields}

    def wake(self):
        for kind, offset, fields in (
            ('wake_observed', 30000, {'idle_seconds': 29999, 'idle_evidence_revision': 2}),
            ('wake_connected', 30002, {'connected_seconds': 2}),
            ('wake_first_output', 30004, {'first_output_seconds': 4}),
        ):
            self.events.append(self.event(kind, offset, detected_epoch=self.start + 30000, **fields))

    def report(self, **kwargs):
        return summary.analyze(self.plan, self.status, self.rows, self.events, kwargs.pop('now', self.end + 1), **kwargs)

    def test_complete_coverage_is_reviewable_not_product_completion(self):
        result = self.report()
        self.assertEqual(result['status'], 'ready_for_review')
        self.assertEqual(result['coverage_percent'], 100)
        self.assertEqual(result['qualified_long_idle_wakes'], 1)
        self.assertFalse(result['overall_goal_complete'])
        self.assertEqual(len(result['hourly_browser_rss']), 24)

    def test_legacy_idle_counter_is_not_strong_long_idle_evidence(self):
        self.events[-3].pop('idle_evidence_revision')
        self.assertEqual(self.report()['qualified_long_idle_wakes'], 0)

    def test_gap_during_wake_does_not_qualify_as_confirmed_long_idle_wake(self):
        self.events[-1]['observation_gap'] = True
        self.events.append(self.event('observation_gap', 30003, reason='poll_failed'))
        result = self.report()
        self.assertEqual(result['qualified_long_idle_wakes'], 0)
        self.assertIn('observation_gaps_require_review', result['review_items'])

    def test_future_rows_and_completion_do_not_make_partial_run_pass(self):
        result = self.report(now=self.start + 3600)
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['elapsed_hours'], 1)
        self.assertEqual(result['valid_metric_samples'], 240)
        self.assertLess(result['planned_window_coverage_percent'], 5)
        self.assertEqual(result['qualified_long_idle_wakes'], 0)

    def test_switch_between_samples_does_not_pass_as_one_phrase_run(self):
        self.events.append(self.event('wake_phrase',100,phrase='okay-kai'))
        result=self.report()
        self.assertEqual(result['wake_phrases'],['hey-brain','okay-kai'])
        self.assertIn('mixed_or_unknown_wake_phrases',result['review_items'])
        self.assertEqual(result['status'],'needs_review')

    def test_duplicate_samples_cannot_fill_missing_time(self):
        self.rows = [r for i, r in enumerate(self.rows) if i % 2 == 0 for _ in range(2)]
        result = self.report()
        self.assertEqual(result['coverage_percent'], 50)
        self.assertEqual(result['largest_gap_seconds'], 15)
        self.assertEqual(result['status'], 'needs_review')

    def test_unavailable_health_is_not_valid_coverage(self):
        for row in self.rows[:100]:
            row['health_ms'] = None
        result = self.report(parse_errors=1)
        self.assertEqual(result['invalid_samples'], 101)
        self.assertLess(result['coverage_percent'], 99)
        self.assertIn('invalid_or_unavailable_samples', result['review_items'])

    def test_restarts_and_recovered_alert_remain_visible(self):
        for row in self.rows[100:]:
            row['browser_generation'] = [[11, 200]]
        self.events.extend([self.event('backend_instance_changed', 2000),
                            self.event('observer_started', 2010),
                            self.event('alert', 3000, code='browser_cpu_idle_high'),
                            self.event('recovered', 3400, code='browser_cpu_idle_high')])
        result = self.report()
        self.assertEqual(result['browser_generation_changes'], 1)
        self.assertEqual(result['backend_instance_changes'], 1)
        self.assertEqual(result['observer_starts'], 2)
        self.assertEqual(result['alerts'], ['browser_cpu_idle_high'])
        self.assertEqual(result['status'], 'needs_review')

    def test_clock_backwards_requires_review_even_with_full_coverage(self):
        self.rows[1], self.rows[2] = self.rows[2], self.rows[1]
        self.assertIn('clock_moved_backwards', self.report()['review_items'])

    def test_long_silence_is_not_a_real_wake(self):
        self.events = self.events[:2]
        self.assertIn('real_wake_after_eight_hours_missing', self.report()['review_items'])

    def test_wake_needs_correlated_output_and_fast_connection(self):
        for failure in ('missing_output', 'wrong_session', 'slow', 'failed', 'idle_before_run'):
            with self.subTest(failure=failure):
                self.events = self.events[:2]
                self.wake()
                if failure == 'missing_output': self.events.pop()
                if failure == 'wrong_session': self.events[-1]['detected_epoch'] += 1
                if failure == 'slow': self.events[-2]['connected_seconds'] = 20
                if failure == 'failed': self.events.append(self.event('wake_failed', 30005, detected_epoch=self.start + 30000))
                if failure == 'idle_before_run': self.events[-3]['idle_seconds'] = 40000
                self.assertEqual(self.report()['qualified_long_idle_wakes'], 0)

    def test_completion_requires_matching_plan_and_marker(self):
        self.status['start_epoch'] += 1
        self.assertEqual(self.report()['status'], 'pending')
        self.status['start_epoch'] -= 1
        self.events = [e for e in self.events if e['type'] != 'observation_complete']
        self.assertEqual(self.report()['status'], 'pending')

    def test_idle_statistics_exclude_recording_load(self):
        self.rows[1]['activity'] = 'recording'
        self.rows[1]['browser']['cpu_percent'] = 400
        result = self.report()
        self.assertEqual(result['idle_browser_cpu_percent_of_one_core']['max'], 12)
        self.assertEqual(summary.distribution(range(1, 101))['p95'], 95)

    def test_empty_or_invalid_data_cannot_pass(self):
        self.rows = [None, {'at': 'bad'}, {'at': '2026-10-15T16:00:00'}]
        self.events = []
        result = self.report()
        self.assertEqual(result['status'], 'pending')
        self.assertEqual(result['valid_metric_samples'], 0)
        self.assertEqual(result['invalid_samples'], 3)
        self.assertIn('observer_start_evidence_missing', result['review_items'])

    def test_malformed_jsonl_is_counted_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'rows.jsonl'
            path.write_text('{"valid": true}\n{partial\n')
            rows, errors = summary.read_lines(path)
        self.assertEqual(rows, [{'valid': True}])
        self.assertEqual(errors, 1)


if __name__ == '__main__':
    unittest.main()
