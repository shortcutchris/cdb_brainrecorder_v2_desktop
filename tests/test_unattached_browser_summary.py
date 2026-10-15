"""Prevent incomplete or incomparable local measurements becoming evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.summarize_unattached_browser import summarize


class UnattachedBrowserSummaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = dict(planned_seconds=1800, started_at_epoch=10000, browser_pid=1,
                         scope='synthetic fixture', chrome_version='test',
                         preview_backend_version='test', frontend_hashes={}, limitations=[])
        self.rows = [dict(root_pid=1, elapsed_seconds=t, at_epoch=10000+t,
                          processes=[dict(pid=1, parent=999, name='Chrome', rss_kib=1024+t)],
                          browser_rss_kib=1024+t, proxy_errors=0,
                          request_counts={'/api/state': t+1, '/api/wake/status': t+1})
                     for t in range(0, 1801, 60)]
        self.cleanup = dict(closed=True, completed_observation=True,
                            proxy_thread_stopped=True, remaining_processes='', at_epoch=11802)

    def evaluate(self):
        for name, value in {'plan.json': self.plan, 'cleanup.json': self.cleanup,
                            'sampler-complete.json': dict(completed=True, elapsed_seconds=1800, at_epoch=11801),
                            'proxy-counters.json': dict(errors=[])}.items():
            (self.root/name).write_text(json.dumps(value))
        (self.root/'process-memory.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.rows))
        return summarize(self.root)

    def test_completed_local_run_is_not_goal_acceptance(self):
        report = self.evaluate()
        self.assertTrue(report['completed_local_observation'])
        self.assertFalse(report['overall_goal_complete'])
        self.assertEqual(report['browser_rss_delta_mib'], 1680/1024)

    def test_truncated_run_rejected(self):
        self.rows.pop()
        with self.assertRaisesRegex(ValueError, 'planned interval'):
            self.evaluate()

    def test_sampling_gap_rejected(self):
        del self.rows[10:12]
        with self.assertRaisesRegex(ValueError, 'measurement interval'):
            self.evaluate()

    def test_polling_stall_rejected(self):
        self.rows[10]['request_counts'] = self.rows[9]['request_counts'].copy()
        with self.assertRaisesRegex(ValueError, 'polling stopped'):
            self.evaluate()

    def test_unclean_exit_rejected(self):
        self.cleanup['closed'] = False
        with self.assertRaisesRegex(ValueError, 'Cleanup'):
            self.evaluate()

    def test_unrelated_process_rejected(self):
        self.rows[-1]['processes'].append(dict(pid=2, parent=987, name='Other', rss_kib=0))
        with self.assertRaisesRegex(ValueError, 'Unrelated'):
            self.evaluate()

    def test_renderer_restart_rejected(self):
        self.rows[-1]['processes'].append(dict(pid=2, parent=1, name='Renderer', rss_kib=0))
        with self.assertRaisesRegex(ValueError, 'process set changed'):
            self.evaluate()

    def test_zero_resident_zombie_does_not_create_false_restart(self):
        self.rows[15]['processes'].append(dict(pid=3, parent=1, name='<defunct>', rss_kib=0))
        self.assertTrue(self.evaluate()['completed_local_observation'])

    def test_wrong_rss_sum_rejected(self):
        self.rows[-1]['browser_rss_kib'] += 1
        with self.assertRaisesRegex(ValueError, 'RSS total'):
            self.evaluate()
