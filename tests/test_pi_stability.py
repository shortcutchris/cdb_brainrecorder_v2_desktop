import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('observe_pi_stability', Path(__file__).parents[1] / 'scripts/observe_pi_stability.py')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class StabilityTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.observer = monitor.Observer(self.events.append)

    def row(self, cpu=95, memory=300, mode='idle', generation=1):
        return {'browser': {'cpu_percent': cpu, 'rss_mb': memory, 'processes': 4},
                'activity': mode, 'browser_generation': generation, 'available_mb': 12000, 'temperature_c': 50}

    def test_short_spike_does_not_alert(self):
        for t in range(0, 90, 15):
            self.observer.sample(self.row(), t)
        self.assertFalse(self.events)

    def test_sustained_idle_cpu_alerts_once_and_recovers(self):
        for t in range(0, 400, 15):
            self.observer.sample(self.row(), t)
        self.assertEqual([e['code'] for e in self.events], ['browser_cpu_idle_high'])
        self.observer.sample(self.row(cpu=10), 405)
        self.assertEqual(self.events[-1]['type'], 'recovered')

    def test_recording_pause_and_live_load_do_not_raise_idle_alarm(self):
        for mode in ('recording', 'paused', 'live-active', 'processing', 'unknown'):
            o = monitor.Observer(self.events.append)
            for t in range(0, 400, 15):
                o.sample(self.row(mode=mode), t)
        self.assertFalse(self.events)

    def test_memory_alert_is_reported_during_recording_without_actions(self):
        for t in range(0, 400, 15):
            self.observer.sample(self.row(memory=1800, mode='recording'), t)
        self.assertEqual([e['code'] for e in self.events], ['browser_memory_high'])

    def test_growth_does_not_compare_different_browser_generations(self):
        self.observer.sample(self.row(memory=100), 0)
        self.observer.sample(self.row(memory=600, generation=2), 1800)
        self.assertFalse(self.events)
        self.observer.sample(self.row(memory=900, generation=2), 3600)
        self.assertEqual(self.events[-1]['code'], 'browser_memory_growth')

    def test_pid_reuse_does_not_create_false_cpu_spike(self):
        old = {2: {'ticks': 100, 'start': 1}}
        new = {2: {'ticks': 1000000, 'start': 2, 'rss_mb': 30, 'renderer': True}}
        with patch.object(monitor.os, 'sysconf', return_value=100):
            self.assertEqual(monitor.process_metrics(new, old, 15)['cpu_percent'], 0)

    def test_only_kiosk_profile_and_its_children_are_measured(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for pid, ppid, profile in ((1, 0, '/kiosk'), (2, 1, None), (3, 0, '/other')):
                d = root / str(pid)
                d.mkdir()
                fields = ['0'] * 22
                fields[0], fields[1], fields[19], fields[21] = 'S', str(ppid), '123', '100'
                (d / 'stat').write_text(f'{pid} (chromium) ' + ' '.join(fields))
                (d / 'comm').write_text('chromium')
                (d / 'cmdline').write_bytes(b'chromium\0' + (f'--user-data-dir={profile}'.encode() if profile else b'--type=renderer') + b'\0')
            with patch.object(monitor.os, 'sysconf', return_value=4096):
                rows, roots = monitor.browser_processes(root, '/kiosk')
            self.assertEqual(set(rows), {1, 2})
            self.assertEqual(roots, {1})
            (root / '1/cmdline').write_bytes(b'/usr/lib/chromium/chromium --user-data-dir=/kiosk http://127.0.0.1:8088/\0')
            (root / '2/cmdline').write_bytes(b'/usr/lib/chromium/chromium --type=renderer --user-data-dir=/kiosk\0')
            with patch.object(monitor.os, 'sysconf', return_value=4096):
                rows, roots = monitor.browser_processes(root, '/kiosk')
            self.assertEqual(set(rows), {1, 2})
            self.assertTrue(rows[2]['renderer'])
            self.assertEqual(roots, {1})

    def test_wake_latency_after_idle_and_output(self):
        wake = {'instance': 'a', 'detections': 0, 'state': 'listening'}
        self.observer.poll(wake, {'state': 'idle', 'active': False}, 1)
        wake = {**wake, 'detections': 1, 'state': 'suspended'}
        self.observer.poll(wake, {'state': 'connecting', 'active': True}, 3600)
        self.observer.poll(wake, {'state': 'listening', 'active': True}, 3603)
        self.observer.poll(wake, {'state': 'speaking', 'active': True, 'output': {'active': True}}, 3604)
        self.assertEqual(self.observer.pending['idle_seconds'], 3599)
        self.assertEqual(self.observer.pending['connected_seconds'], 3)
        self.assertEqual(self.observer.pending['first_output_seconds'], 4)

    def test_backend_restart_is_not_a_new_wake(self):
        self.observer.poll({'instance': 'a', 'detections': 4}, {'state': 'idle'}, 10)
        self.observer.poll({'instance': 'b', 'detections': 0}, {'state': 'idle'}, 20)
        self.assertEqual(self.observer.counts['wake_observed'], 0)

    def test_stalled_start_and_status_failure_report_once(self):
        self.observer.poll({'instance': 'a', 'detections': 0}, {'state': 'idle'}, 1)
        self.observer.poll({'instance': 'a', 'detections': 1}, {'state': 'connecting'}, 2)
        self.observer.poll({'instance': 'a', 'detections': 1}, {'state': 'connecting'}, 18)
        self.assertIn('wake_connect_slow', self.observer.alerts)
        for t in range(20, 25):
            self.observer.failed(t)
        self.assertEqual(sum(e.get('code') == 'status_unreachable' for e in self.events), 1)

    def test_detection_status_race_does_not_report_false_failure(self):
        self.observer.poll({'instance': 'a', 'detections': 0}, {'state': 'ended'}, 1)
        self.observer.poll({'instance': 'a', 'detections': 1}, {'state': 'ended'}, 2)
        self.observer.poll({'instance': 'a', 'detections': 1}, {'state': 'listening', 'active': True}, 3)
        self.assertEqual(self.observer.counts['wake_failed'], 0)
        self.assertEqual(self.observer.counts['wake_connected'], 1)


if __name__ == '__main__':
    unittest.main()
