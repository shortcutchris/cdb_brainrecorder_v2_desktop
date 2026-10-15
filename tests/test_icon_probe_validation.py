"""Regression gates for wrong-source, missing-image and incomplete diagnostics."""
import copy
import unittest
from scripts.validate_icon_probe import EXPECTED_RESPONSES, validate

CANDIDATE = 'c' * 64


def fixture():
    report = {'revision': 4, 'mode': 'guarded', 'browser': {'product': 'Chrome/142.0.7444.59'},
              'planned_seconds': 300, 'errors': [], 'guard_samples': [{'idle': True}],
              'auxiliary_statuses': dict(EXPECTED_RESPONSES),
              'known_production_missing_assets': ['/assets/InterVariable.woff2'],
              'source_hashes': {'candidate_microphone.js': CANDIDATE,
                                'microphone.js': 'a' * 64, 'served_microphone.js': CANDIDATE},
              'browser_pid': 10, 'runs': []}
    for i in range(11):
        report['runs'].append({'at_epoch': 1000 + i * 30, 'processes': {'10': {'start': 123}},
                              'ui': {'workspace': 'start-view', 'hidden': False, 'online': True,
                                     'version': '0.5.55', 'probeSource': '/assets/play.svg', 'probeReady': True,
                                     'errorCounts': {'script': 0, 'rejection': 0}},
                              'response_errors': [], 'requests': {'/api/state': i * 30 + 1, '/api/wake/status': i * 100 + 1}})
    cleanup = {'closed': True, 'remaining': [], 'server_stopped': True,
               'guard_stopped': True, 'profile_written': True}
    return report, cleanup


class IconProbeValidationTests(unittest.TestCase):
    def test_valid_probe_still_is_not_overall_stability_or_complete_asset_health(self):
        report, cleanup = fixture()
        result = validate(report, cleanup, CANDIDATE, 'guarded')
        self.assertTrue(result['probe_valid'])
        self.assertFalse(result['overall_goal_complete'])
        self.assertFalse(result['all_production_assets_healthy'])

    def test_incorrect_helper_copy_is_rejected_even_if_service_finished(self):
        report, cleanup = fixture()
        report['source_hashes']['served_microphone.js'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'Wrong served source'):
            validate(report, cleanup, CANDIDATE, 'guarded')

    def test_candidate_hash_must_match_independent_committed_source(self):
        report, cleanup = fixture()
        with self.assertRaisesRegex(ValueError, 'committed source'):
            validate(report, cleanup, 'd' * 64, 'guarded')

    def test_bad_icon_and_script_errors_cannot_pass_with_correct_hash(self):
        for field, value in [('probeSource', 'play'), ('probeReady', False),
                             ('errorCounts', {'script': 0, 'rejection': 1})]:
            report, cleanup = fixture(); report['runs'][5]['ui'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(report, cleanup, CANDIDATE, 'guarded')

    def test_cancellation_and_live_children_rejected(self):
        for field, value in [('profile_written', False), ('remaining', [11]), ('closed', False)]:
            report, cleanup = fixture(); cleanup[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(report, cleanup, CANDIDATE, 'guarded')

    def test_missing_auxiliary_or_unexpected_static_error_rejected(self):
        report, cleanup = fixture(); report['auxiliary_statuses']['/api/cdb/areas'] = 404
        with self.assertRaises(ValueError): validate(report, cleanup, CANDIDATE, 'guarded')
        report, cleanup = fixture(); report['runs'][3]['response_errors'] = [{'path': '/play'}]
        with self.assertRaises(ValueError): validate(report, cleanup, CANDIDATE, 'guarded')

    def test_incomplete_duration_stalled_polling_and_reused_pid_rejected(self):
        report, cleanup = fixture()
        changes = [lambda r: r['runs'].pop(),
                   lambda r: r['runs'][4]['requests'].update(r['runs'][3]['requests']),
                   lambda r: r['runs'][7]['processes']['10'].update(start=124)]
        for change in changes:
            altered = copy.deepcopy(report); change(altered)
            with self.assertRaises(ValueError): validate(altered, cleanup, CANDIDATE, 'guarded')

    def test_original_is_checked_against_its_own_source(self):
        report, cleanup = fixture(); report['mode'] = 'original'
        with self.assertRaises(ValueError): validate(report, cleanup, CANDIDATE, 'original')
        report['source_hashes']['served_microphone.js'] = 'a' * 64
        self.assertTrue(validate(report, cleanup, CANDIDATE, 'original')['probe_valid'])
