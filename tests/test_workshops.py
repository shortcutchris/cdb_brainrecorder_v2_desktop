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
