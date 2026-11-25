import copy
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from services.workflow_catalog import WorkflowCatalog, validate, load_definition, digest
from services.workshops import Workshops


class CatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = WorkflowCatalog(self.root)
        self.definition = self.catalog.get('retrospective')

    def candidate(self):
        value = copy.deepcopy(self.definition)
        value.update(id='project_briefing', name='Projektbriefing', voice_aliases=['Projekt klären'])
        return value

    def test_fresh_catalog_and_inert_agent_proposal(self):
        self.assertEqual(len(self.catalog.list()), 3)
        self.assertEqual(self.catalog.path.stat().st_mode & 0o777, 0o600)
        sha = self.catalog.propose(self.candidate(), origin='agent')
        self.assertEqual(self.catalog.proposals()[0]['state'], 'draft')
        with self.assertRaises(ValueError): self.catalog.activate(sha)
        with self.assertRaises(ValueError): self.catalog.get('project_briefing')
        self.catalog.approve(sha, reviewer='Testoperator')
        with self.assertRaises(ValueError): self.catalog.get('project_briefing')
        self.catalog.activate(sha)
        self.assertEqual(WorkflowCatalog(self.root).get('project_briefing'), self.candidate())
        self.assertEqual(self.catalog.propose(self.candidate(), origin='agent'), sha)

    def test_immutable_versions_exact_review_and_rollback(self):
        one = self.candidate(); first = self.catalog.propose(one)
        self.catalog.approve(first, reviewer='Testoperator'); self.catalog.activate(first)
        changed = copy.deepcopy(one); changed['description'] = 'Neuer Ablauf'
        with self.assertRaises(ValueError): self.catalog.propose(changed)
        changed['version'] = 2; second = self.catalog.propose(changed)
        with self.assertRaises(ValueError): self.catalog.approve('0'*64, reviewer='Testoperator')
        with self.assertRaises(ValueError): self.catalog.approve(second, reviewer='')
        self.catalog.approve(second, reviewer='Testoperator'); self.catalog.activate(second)
        self.assertEqual(self.catalog.get(one['id'])['version'], 2)
        self.catalog.activate(first)
        self.assertEqual(self.catalog.get(one['id'])['version'], 1)
        self.catalog.retire(one['id'])
        with self.assertRaises(ValueError): self.catalog.get(one['id'])

    def test_alias_collision_is_rejected_on_activation(self):
        value = self.candidate(); value['voice_aliases'] = ['  BRAINSTORMING  ']
        sha = self.catalog.propose(value); self.catalog.approve(sha, reviewer='Testoperator')
        with self.assertRaises(ValueError): self.catalog.activate(sha)
        value['version'] += 1; value['voice_aliases'] = ['Freies Gespräch']
        sha = self.catalog.propose(value); self.catalog.approve(sha, reviewer='Testoperator')
        with self.assertRaises(ValueError): self.catalog.activate(sha)

    def test_schema_rejects_executable_unknown_duplicate_and_unbounded_inputs(self):
        changes = [dict(script='import os'), dict(url='https://example.com'), dict(schema_version=2),
                   dict(version=True), dict(default_minutes=60), dict(outputs=['shell']),
                   dict(id='../escape'), dict(id='free_talk'), dict(moderation='x'*3001),
                   dict(sections=[]), dict(phases=[]), dict(voice_aliases=[])]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError): validate(self.definition | change)
        duplicate = copy.deepcopy(self.definition); duplicate['sections'].append(duplicate['sections'][0])
        with self.assertRaises(ValueError): validate(duplicate)
        path = self.root/'bad.json'; path.write_text('{"id":"a","id":"b"}')
        with self.assertRaises(ValueError): load_definition(path)
        path.write_text('x'*32001)
        with self.assertRaises(ValueError): load_definition(path)


class WorkflowRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.binding = {'server':'synthetic', 'user_id':'test', 'client_id':'test'}
        self.current = self.binding
        self.store = Workshops(self.tmp.name, SimpleNamespace(generation=0), lambda:self.current)
        self.scope = {'binding':self.binding,'handle':'test-connection','workshop_id':None,'device_tools_version':5}
        self.counter = 0

    def command(self, name, args=None, scope=None):
        self.counter += 1
        return self.store.execute(scope or self.scope, {'id':f'request-{self.counter:020d}', 'name':name,
                                  'arguments':args or {}, 'expires_at':time.time()+60})

    def test_unicode_results_remain_below_relay_limit_without_losing_saved_text(self):
        row=self.store.create(self.binding,'retrospective','Test','Ziel',10)
        row=self.store.edit(self.binding,row['id'],1,section='strengths',text='🧠'*6000)
        with self.assertRaises(ValueError):
            self.store.edit(self.binding,row['id'],2,section='challenges',text='🧠'*5000)
        saved=self.store.get(self.binding,row['id'])
        self.assertEqual(saved['revision'],2)
        self.assertEqual(saved['sections']['strengths'],'🧠'*6000)
        self.assertEqual(saved['sections']['challenges'],'')
        self.assertLess(len(json.dumps({'ok':True,'workshop':self.store.voice_row(saved),'approved_workflow':saved['workflow']})),128*1024)

    def test_third_format_has_real_dynamic_steps_and_results(self):
        self.assertEqual(self.command('list_workshop_formats',scope=self.scope | {'handle':None})['code'],'invalid_scope')
        catalog = self.command('list_workshop_formats')
        self.assertIn('retrospective', [r['id'] for r in catalog['formats']])
        choice = self.command('request_workshop_mode', {'format':'retrospective'})
        self.assertIsNone(choice['active_workshop_id'])
        started = self.command('answer_workshop_intro', {'choice_id':choice['choice_id'], 'answer':'explain'})
        row = started['workshop']; self.assertEqual(row['format'],'retrospective')
        self.assertEqual(started['approved_workflow']['id'], row['format'])
        self.assertIn('challenges', row['sections']); self.assertNotIn('ideas', row['sections'])
        result = self.command('update_workshop_result', {'section':'challenges','text':'Synthetische Herausforderung','revision':1})
        self.assertTrue(result['ok'])
        result = self.command('set_workshop_phase', {'phase':'learning','revision':2})
        self.assertTrue(result['ok'])
        self.assertFalse(self.command('update_workshop_result', {'section':'ideas','text':'Wrong','revision':3})['ok'])
        self.assertFalse(self.command('set_workshop_phase', {'phase':'unknown','revision':3})['ok'])
        meta = self.store.list(self.binding)[0]
        self.assertEqual(meta['artifacts'][1]['title'],'Was war schwierig?')

    def test_snapshot_survives_catalog_update_and_restart(self):
        old = self.store.create(self.binding,'retrospective','Test','Ziel',10)
        new = self.store.catalog.get('retrospective'); new['version']=2; new['sections'][1]['label']='Neue Beschriftung'
        sha=self.store.catalog.propose(new); self.store.catalog.approve(sha,reviewer='Test'); self.store.catalog.activate(sha)
        fresh=Workshops(self.tmp.name,SimpleNamespace(generation=0),lambda:self.current)
        self.assertEqual(fresh.get(self.binding,old['id'])['workflow']['version'],1)
        self.assertEqual(fresh.create(self.binding,'retrospective','Neu','Ziel',10)['workflow']['version'],2)
        self.assertEqual(fresh.get(self.binding,old['id'])['workflow_digest'],digest(old['workflow']))

    def test_pending_definition_pinned_and_retirement_blocks_new_start(self):
        pending=self.command('request_workshop_mode',{'format':'retrospective'})
        new=self.store.catalog.get('retrospective');new['version']=2
        sha=self.store.catalog.propose(new);self.store.catalog.approve(sha,reviewer='Test');self.store.catalog.activate(sha)
        started=self.command('answer_workshop_intro',{'choice_id':pending['choice_id'],'answer':'skip'})
        self.assertEqual(started['approved_workflow']['version'],1)
        self.command('request_workshop_mode',{'format':'free_talk'})
        free=self.command('get_workshop')['pending_intro']
        self.command('answer_workshop_intro',{'choice_id':free['choice_id'],'answer':'skip'})
        pending=self.command('request_workshop_mode',{'format':'retrospective'})
        self.store.catalog.retire('retrospective')
        self.assertFalse(self.command('answer_workshop_intro',{'choice_id':pending['choice_id'],'answer':'skip'})['ok'])
        self.assertIsNone(self.command('get_workshop')['active_workshop_id'])

    def test_old_clients_cannot_execute_new_workflows(self):
        for version in (1,2,3,4):
            scope=self.scope|{'device_tools_version':version}
            self.assertFalse(self.command('list_workshop_formats',scope=scope)['ok'])
            self.assertFalse(self.command('request_workshop_mode',{'format':'retrospective'},scope)['ok'])
        row=self.store.create(self.binding,'retrospective','Test','Ziel',10)
        scope=self.scope|{'device_tools_version':3,'workshop_id':row['id']}
        self.assertFalse(self.command('get_workshop',scope=scope)['ok'])

    def test_outputs_are_permissions_not_a_prompt_suggestion(self):
        recipe=self.store.catalog.get('retrospective');recipe['version']=2;recipe['outputs']=[]
        sha=self.store.catalog.propose(recipe);self.store.catalog.approve(sha,reviewer='Test');self.store.catalog.activate(sha)
        row=self.store.create(self.binding,'retrospective','Test','Ziel',10)
        with self.assertRaises(ValueError):self.store.save(self.binding,row['id'],1)
        with self.assertRaises(ValueError):self.store.save_brain(self.binding,row['id'],1,['goal'],'test-area')
        self.current=None
        self.assertFalse(self.command('list_workshop_formats')['ok'])

    def test_upgrade_keeps_old_fields_and_assigns_the_legacy_snapshot_once(self):
        row=self.store.create(self.binding,'interview','Alt','Bestehendes Ziel',10)
        old=copy.deepcopy(row);old.pop('workflow');old.pop('workflow_digest')
        with self.store.db() as db:db.execute('UPDATE drafts SET data=? WHERE id=?',(json.dumps(old),row['id']))
        fresh=Workshops(self.tmp.name,SimpleNamespace(generation=0),lambda:self.current)
        upgraded=fresh.get(self.binding,row['id'])
        self.assertEqual({k:upgraded[k] for k in old},old)
        self.assertEqual(upgraded['workflow']['id'],'interview')
        self.assertEqual(upgraded['revision'],1)


if __name__ == '__main__': unittest.main()
