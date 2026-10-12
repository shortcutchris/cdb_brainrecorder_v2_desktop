import json
import tempfile
from pathlib import Path
import threading
import unittest
from services.evidence_summary import EvidenceSummary,validate_items
from meeting_recorder.processing import summarize


def response(tasks=None,events=None,decisions=None,open_points=None):
    return {'tasks':tasks or [],'events':events or [],'decisions':decisions or [],'open_points':open_points or []}

class EvidenceTests(unittest.TestCase):
    def test_invented_action_and_name_and_deadline_cannot_become_facts(self):
        source='AA erstellt die Prüfliste bis Mittwoch. Die Zuständigkeit ist unklar.'
        raw=response(tasks=[{'quote':source,'action':'Zuständigen benennen','owner':'Ben','due':'Donnerstag'}, {'quote':'AA erstellt die Prüfliste bis Mittwoch.','action':'erstellt die Prüfliste','owner':'Anna','due':'Freitag'}])
        result=validate_items(source,raw)
        self.assertEqual(result['rejected'],1)
        task=result['tasks'][0];self.assertIsNone(task['owner']);self.assertIsNone(task['due']);self.assertTrue(task['unclear_owner'])
        self.assertEqual(task['text'],'erstellt die Prüfliste')

    def test_short_name_is_marked_and_question_is_not_an_assignment(self):
        source='AA erstellt die Prüfliste bis Mittwoch. Wen prüft das Mikrofon am Donnerstag?'
        result=validate_items(source,response(tasks=[{'quote':'AA erstellt die Prüfliste bis Mittwoch.','action':'erstellt die Prüfliste','owner':'AA','due':'Mittwoch'}, {'quote':'Wen prüft das Mikrofon am Donnerstag?','action':'prüft das Mikrofon','owner':'Wen','due':'Donnerstag'}]))
        self.assertEqual(len(result['tasks']),1);self.assertTrue(result['tasks'][0]['unclear_owner'])
        self.assertEqual(len(result['open_points']),1);self.assertTrue(result['open_points'][0]['uncertain'])

    def test_proposals_budget_and_unapproved_orders_are_not_tasks_or_decisions(self):
        quotes=['Vielleicht kaufen wir einen Lautsprecher.','Das Budget beträgt 400 Euro.','Die Bestellung ist nicht freigegeben.']
        source=' '.join(quotes)
        raw=response(tasks=[{'quote':q,'action':q,'owner':None,'due':None} for q in quotes],decisions=[{'quote':q,'text':q} for q in quotes])
        result=validate_items(source,raw);self.assertFalse(result['tasks']);self.assertFalse(result['decisions'])
        self.assertEqual(result['rejected'],6)

    def test_owner_and_due_cannot_be_borrowed_from_adjacent_sentence(self):
        source='Anna erstellt die Prüfliste bis Mittwoch. Ben prüft das Mikrofon am Donnerstag.'
        result=validate_items(source,response(tasks=[{'quote':source,'action':'prüft das Mikrofon','owner':'Anna','due':'Mittwoch'}]))
        self.assertIsNone(result['tasks'][0]['owner']);self.assertIsNone(result['tasks'][0]['due'])

    def test_exact_evidence_preserved_across_real_multi_part_engine_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);source='Testprojekt Nummer 1. Anna erstellt die Prüfliste bis Mittwoch. '+('Hintergrundinformation. '*300)+'Testprojekt Nummer 2. AA erstellt die Prüfliste bis Mittwoch.'
            calls=[]
            def generate(part,instructions):
                calls.append(part);tasks=[]
                for owner in ['Anna','AA']:
                    q=owner+' erstellt die Prüfliste bis Mittwoch.'
                    if q in part:tasks.append({'quote':q,'action':'erstellt die Prüfliste','owner':owner,'due':'Mittwoch'})
                return json.dumps(response(tasks=tasks))
            config={'chunk_chars':3000,'prompt':'Schreibe auf Deutsch nur diese drei Abschnitte: Aufgaben, Termine, Offene Punkte.'}
            class Backend:
                def generate(self,part,c,merge=False):return EvidenceSummary(folder,source,c,generate).generate(part,merge)
            output=summarize(source,config,Backend(),threading.Event(),lambda _:None)
            self.assertIn('Anna: erstellt die Prüfliste',output);self.assertIn('Name unklar (Transkript: „AA“)',output)
            self.assertIn('Projekt 1',output);self.assertIn('Projekt 2',output)
            first=len(calls);again=summarize(source,config,Backend(),threading.Event(),lambda _:None)
            self.assertEqual(output,again);self.assertEqual(len(calls),first)
            review=json.loads((folder/'task-evidence/review.json').read_text());self.assertEqual(len(review['items']['tasks']),2)

    def test_missing_invalid_evidence_and_partial_merges_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary=EvidenceSummary(Path(tmp),'Anna erstellt die Prüfliste. '+('Hintergrund. '*300),{'chunk_chars':3000},lambda *_:'not json')
            with self.assertRaisesRegex(ValueError,'gültige'):summary.generate(summary.parts[0])
            with self.assertRaisesRegex(ValueError,'Unvollständige'):summary.generate('some missing receipt',True)
            with self.assertRaises(ValueError):validate_items('Source',{'tasks':[]})

    def test_unknown_project_label_does_not_inherit_previous_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            source='Testprojekt Nummer 1. Hintergrund. Testprojekt X. AA erstellt die Prüfliste bis Mittwoch.'
            raw=response(tasks=[{'quote':'AA erstellt die Prüfliste bis Mittwoch.','action':'erstellt die Prüfliste','owner':'AA','due':'Mittwoch'}])
            output=EvidenceSummary(Path(tmp),source,{'chunk_chars':6000},lambda *_:json.dumps(raw)).generate(source)
            self.assertIn('Projektzuordnung unklar',output);self.assertNotIn('· Projekt 1',output)
