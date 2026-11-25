import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from services.workshops import Workshops


class WorkshopsTest(unittest.TestCase):
    def test_brain_selection_uses_reviewed_revision_and_only_selected_text(self):
        from unittest.mock import Mock
        self.cdb.enqueue_artifacts = Mock(return_value={'ok': True})
        self.store.edit(self.binding, self.row['id'], 1, section='ideas', text='Nur diese Idee')
        result = self.store.save_brain(self.binding, self.row['id'], 2, ['ideas'], 'area')
        self.assertTrue(result['ok'])
        args = self.cdb.enqueue_artifacts.call_args.args
        self.assertEqual(args[:2], (self.binding, 'area'))
        self.assertEqual(args[2], [{'section': 'ideas', 'title': 'Synthetisches Interview · Ideen', 'content': '# Ideen\n\nNur diese Idee'}])
        self.assertNotIn('Arbeitsweise verstehen', str(args[2]))
        for revision, sections in [(1, ['ideas']), (2, []), (2, ['unknown']), (2, ['ideas','ideas']), (2, ['findings'])]:
            with self.assertRaises(ValueError): self.store.save_brain(self.binding, self.row['id'], revision, sections, 'area')
        self.assertEqual(self.cdb.enqueue_artifacts.call_count, 1)
        self.current = None
        with self.assertRaises(ValueError): self.store.save_brain(self.binding, self.row['id'], 2, ['ideas'], 'area')

    def test_chat_metadata_exposes_asset_labels_but_not_result_text(self):
        self.store.edit(self.binding, self.row['id'], 1, section='ideas', text='Privater Inhalt')
        meta = self.store.list(self.binding)[0]
        self.assertEqual([a['section'] for a in meta['artifacts']], ['goal', 'ideas'])
        self.assertNotIn('Privater Inhalt', json.dumps(meta))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.binding = {'server': 'https://staging.cdbos.de', 'user_id': 'synthetic', 'client_id': 'tenant'}
        self.current = dict(self.binding)
        self.calls, self.jobs = [], []
        self.cdb = SimpleNamespace(generation=0, call=self.call)
        self.store = Workshops(self.tmp.name, self.cdb, lambda: self.current, spawn=self.jobs.append)
        self.row = self.store.create(self.binding, 'interview', 'Synthetisches Interview', 'Arbeitsweise verstehen', 10)

    def call(self, path, body, binding):
        self.assertEqual(path, '/api/v1/kb/voice/board-tools/call')
        self.assertEqual(binding, self.binding)
        self.calls.append(body)
        return {'success': True, 'data': {'board_id': 123, 'node_id': 'note-' + str(len(self.calls))}}

    def request(self, name, arguments=None, ident='request-00000000000001'):
        return self.store.execute({'binding': self.binding, 'handle': 'session', 'workshop_id': self.row['id']},
                                  {'id': ident, 'name': name, 'arguments': arguments or {}, 'expires_at': time.time() + 60})

    def test_owner_and_environment_isolation_and_anonymous_read(self):
        self.assertEqual(self.store.list(None), [])
        self.current = {**self.binding, 'user_id': 'another'}
        self.assertEqual(self.store.list(self.current), [])
        with self.assertRaises(ValueError): self.store.get(self.binding, self.row['id'])
        with self.assertRaises(ValueError): self.store.get(self.current, self.row['id'])

    def test_stale_agent_revision_never_overwrites_touch_edit(self):
        self.store.edit(self.binding, self.row['id'], 1, section='findings', text='Vom Menschen korrigiert')
        result = self.request('update_workshop_result', {'section': 'findings', 'text': 'Alt', 'revision': 1})
        self.assertFalse(result['ok'])
        self.assertEqual(self.store.get(self.binding, self.row['id'])['sections']['findings'], 'Vom Menschen korrigiert')

    def test_same_request_cannot_apply_twice(self):
        scope = {'binding': self.binding, 'workshop_id': self.row['id']}
        req = {'id': 'a' * 32, 'name': 'update_workshop_result', 'arguments': {'section': 'ideas', 'text': 'Idee A', 'revision': 1}, 'expires_at': time.time()+60}
        first = self.store.execute(scope, req)
        self.assertTrue(first['ok'])
        self.assertEqual(first, self.store.execute(scope, req))
        req['arguments']['text'] = 'Idee B'
        self.assertEqual(self.store.execute(scope, req)['code'], 'request_conflict')

    def test_pause_blocks_model_writes_but_preserves_manual_edit(self):
        self.store.edit(self.binding, self.row['id'], 1, paused=True)
        self.assertEqual(self.request('set_workshop_phase', {'phase': 'closing', 'revision': 2})['code'], 'workshop_paused')
        row = self.store.edit(self.binding, self.row['id'], 2, section='ideas', text='In der Pause notiert')
        self.assertEqual(row['sections']['ideas'], 'In der Pause notiert')

    def test_only_explicit_save_uses_composer_and_repeated_save_is_noop(self):
        self.assertFalse(self.calls)
        self.assertEqual(self.store.save(self.binding, self.row['id'], 1)['state'], 'queued')
        self.assertFalse(self.calls)
        self.jobs.pop()()
        row = self.store.get(self.binding, self.row['id'])
        self.assertEqual(row['composer']['state'], 'saved')
        self.assertEqual(row['composer']['url'], 'https://composer-staging.cdbos.de/board/123')
        self.assertEqual([c['name'] for c in self.calls], ['create_board', 'add_note', 'add_frame'])
        self.store.save(self.binding, self.row['id'], 1)
        self.assertFalse(self.jobs)

    def test_later_save_appends_snapshot_never_overwrites_composer_user_content(self):
        self.store.save(self.binding, self.row['id'], 1); self.jobs.pop()()
        self.store.edit(self.binding, self.row['id'], 1, section='ideas', text='Idee A')
        self.store.save(self.binding, self.row['id'], 2); self.jobs.pop()()
        self.assertEqual(sum(c['name'] == 'create_board' for c in self.calls), 1)
        self.assertTrue(all(c['name'] in ('create_board','add_note','add_frame') for c in self.calls))

    def test_lost_remote_ack_is_never_retried(self):
        def lost(*a, **kw): raise TimeoutError()
        self.cdb.call = lost
        self.store.save(self.binding, self.row['id'], 1); self.jobs.pop()()
        self.assertEqual(self.store.save(self.binding, self.row['id'], 1)['code'], 'uncertain')
        self.assertFalse(self.jobs)

    def test_logout_stops_unstarted_remote_job_and_hides_its_result(self):
        self.store.save(self.binding, self.row['id'], 1)
        self.current = None; self.cdb.generation += 1
        self.jobs.pop()()
        self.assertFalse(self.calls)
        self.assertEqual(self.store.list(None), [])

    def test_new_edit_during_publication_is_preserved(self):
        self.store.save(self.binding, self.row['id'], 1)
        self.store.edit(self.binding, self.row['id'], 1, section='ideas', text='Spätere Idee')
        self.jobs.pop()()
        row = self.store.get(self.binding, self.row['id'])
        self.assertEqual(row['revision'], 2)
        self.assertEqual(row['composer']['revision'], 1)
        self.assertEqual(row['sections']['ideas'], 'Spätere Idee')

    def test_restart_recovers_draft_and_marks_interrupted_send(self):
        self.store.save(self.binding, self.row['id'], 1)
        fresh = Workshops(self.tmp.name, self.cdb, lambda: self.current, spawn=self.jobs.append)
        self.assertEqual(fresh.get(self.binding, self.row['id'])['composer']['state'], 'uncertain')
        self.assertEqual(Path(fresh.path).stat().st_mode & 0o777, 0o600)

    def test_no_url_or_board_id_accepted_from_model(self):
        self.assertFalse(self.request('save_workshop_to_composer', {'url': 'https://attacker.invalid'})['ok'])
        self.assertFalse(self.request('delete_board', {'board_id': 123})['ok'])

    def test_empty_image_data_directory_and_invalid_input(self):
        with self.assertRaises(ValueError): self.store.create(None, 'interview', 'Test', 'Ziel', 10)
        with self.assertRaises(ValueError): self.store.create(self.binding, 'unknown', 'Test', 'Ziel', 10)
        with self.assertRaises(ValueError): self.store.create(self.binding, 'interview', 'Test', 'Ziel', 60)
        with self.assertRaises(ValueError): self.store.edit(self.binding, self.row['id'], 1, section='ideas', text='x'*6001)
        self.assertNotIn('sections', self.store.list(self.binding)[0])

class SpokenFormatsTest(unittest.TestCase):
    call = WorkshopsTest.call

    def setUp(self):
        WorkshopsTest.setUp(self)
        self.scope = {'binding': self.binding, 'handle': 'voice-session', 'workshop_id': None, 'device_tools_version': 4}
        self.sequence = 0

    def command(self, name, args=None, scope=None):
        self.sequence += 1
        return self.store.execute(scope or self.scope, {'id': f'format-command-{self.sequence:08}', 'name': name,
            'arguments': args or {}, 'expires_at': time.time() + 60})

    def test_intro_waits_and_yes_no_work_for_every_format(self):
        for mode in ('interview', 'brainstorming', 'free_talk'):
            for answer in ('explain', 'skip'):
                before = len(self.store.list(self.binding))
                pending = self.command('request_workshop_mode', {'format': mode})
                self.assertEqual(pending['state'], 'awaiting_explanation_answer')
                self.assertIn('Soll ich', pending['announcement'])
                self.assertEqual(before, len(self.store.list(self.binding)))
                self.assertEqual(self.command('update_workshop_result', {'section': 'ideas', 'text': 'Premature', 'revision': 1})['code'], 'intro_pending')
                started = self.command('answer_workshop_intro', {'choice_id': pending['choice_id'], 'answer': answer})
                self.assertEqual(started['state'], 'started')
                self.assertEqual(started['format'], mode)
                self.assertEqual(bool(started['explanation']), answer == 'explain')
                self.assertTrue(started['opening_question'])
                current = self.command('get_workshop')
                self.assertEqual(current['active_workshop_id'], started['active_workshop_id'])
                self.assertFalse(current['intro_required'])
        self.assertFalse(self.calls); self.assertFalse(self.jobs)

    def test_switch_cancel_expiry_and_account_isolation(self):
        self.scope['workshop_id'] = self.row['id']
        self.assertTrue(self.command('get_workshop')['intro_required'])
        pending = self.command('request_workshop_mode', {'format': 'brainstorming'})
        cancelled = self.command('answer_workshop_intro', {'choice_id': pending['choice_id'], 'answer': 'cancel'})
        self.assertEqual(cancelled['active_workshop_id'], self.row['id'])
        self.assertEqual(len(self.store.list(self.binding)), 1)
        self.assertEqual(self.command('answer_workshop_intro', {'choice_id': pending['choice_id'], 'answer': 'skip'})['code'], 'intro_expired')
        pending = self.command('request_workshop_mode', {'format': 'brainstorming'})
        from unittest.mock import patch
        with patch('services.workshops.time.time', return_value=time.time()+301):
            self.assertEqual(self.command('answer_workshop_intro', {'choice_id': pending['choice_id'], 'answer': 'explain'})['code'], 'intro_expired')
        self.current = self.binding | {'user_id': 'someone-else'}
        self.assertFalse(self.command('get_workshop')['ok'])
        self.current = self.binding
        self.assertEqual(self.store.get(self.binding, self.row['id'])['sections']['goal'], 'Arbeitsweise verstehen')

    def test_duplicate_confirmation_after_scope_change_and_restart_creates_no_duplicate(self):
        pending = self.command('request_workshop_mode', {'format': 'brainstorming'})
        req = {'id': 'one-confirmation-only', 'name': 'answer_workshop_intro',
               'arguments': {'choice_id': pending['choice_id'], 'answer': 'skip'}, 'expires_at': time.time()+60}
        first = self.store.execute(self.scope, req)
        self.scope['workshop_id'] = first['active_workshop_id']
        self.store = Workshops(self.tmp.name, self.cdb, lambda: self.current)
        self.assertEqual(self.store.execute(self.scope, req), first)
        self.assertEqual(len(self.store.list(self.binding)), 2)
        self.assertFalse(self.command('answer_workshop_intro', req['arguments'], self.scope | {'handle': 'other-session'})['ok'])

    def test_manual_format_reuses_existing_draft_and_requires_intro(self):
        self.scope['workshop_id'] = self.row['id']
        pending = self.command('request_workshop_mode', {'format': 'interview'})
        started = self.command('answer_workshop_intro', {'choice_id': pending['choice_id'], 'answer': 'skip'})
        self.assertEqual(started['active_workshop_id'], self.row['id'])
        self.assertIn('anknüpfen', started['opening_question'])
        self.assertEqual(len(self.store.list(self.binding)), 1)
        free = self.command('request_workshop_mode', {'format': 'free_talk'})
        self.command('answer_workshop_intro', {'choice_id': free['choice_id'], 'answer': 'skip'})
        self.assertIsNone(self.command('get_workshop')['active_workshop_id'])
        self.assertEqual(self.store.get(self.binding, self.row['id'])['sections'], self.row['sections'])

    def test_old_protocol_and_invalid_inputs_cannot_start(self):
        for version in (1, 2, 3):
            self.assertEqual(self.command('request_workshop_mode', {'format': 'interview'}, self.scope | {'device_tools_version': version})['code'], 'device_tool_not_negotiated')
        for args in ({'format': 'meeting'}, {'format': []}, {'format': 'brainstorming', 'board_id': 1}):
            self.assertEqual(self.command('request_workshop_mode', args)['code'], 'invalid_arguments')


    def test_additive_upgrade_and_clean_install_keep_private_results_separate(self):
        with self.store.db() as db:
            db.execute('DROP TABLE format_sessions')
        upgraded = Workshops(self.tmp.name, self.cdb, lambda: self.current)
        self.assertEqual(upgraded.get(self.binding, self.row['id'])['sections'], self.row['sections'])
        with upgraded.db() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM format_sessions').fetchone()[0], 0)
        with tempfile.TemporaryDirectory() as fresh:
            clean = Workshops(fresh, self.cdb, lambda: self.current)
            self.assertEqual(clean.list(self.binding), [])
            self.assertEqual(clean.path.stat().st_mode & 0o777, 0o600)
