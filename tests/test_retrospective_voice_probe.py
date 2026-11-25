"""Offline checks for the real read_board text contract; no network or Pi I/O."""
import unittest
from scripts.check_retrospective_composer_voice import contains_facts, verify_readback


class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.titles = {'goal': 'Ziel und Zeitraum', 'actions': 'Vereinbarte Verbesserungen'}
        self.sections = {'goal': 'Workshop am Montag.', 'actions': 'Anna prüft die Technik bis Donnerstag.\nBen versendet die Agenda bis Freitag.'}
        self.text = ('Board "Test"\n3 nodes, 0 edges\n\nFrames:\n'
                     '- [frame-1] "Stand 2" (agent) at (-60, 1700) size 1100×460\n\nNodes:\n'
                     '- [text-1] text (agent) at (0, 1800) size 460×300 in frame frame-1: Ziel und Zeitraum Workshop am Montag.\n'
                     '- [text-2] text (agent) at (520, 1800) size 460×300 in frame frame-1: Vereinbarte Verbesserungen Anna prüft die Technik bis Donnerstag. Ben versendet die Agenda bis Freitag.\n')

    def check(self, text):
        return verify_readback({'text': text}, self.titles, self.sections)

    def test_complete_board_keeps_card_identity_and_normalizes_line_breaks(self):
        result = self.check(self.text)
        self.assertEqual(result['actions']['node_id'], 'text-2')
        self.assertTrue(result['actions']['text_matches_ignoring_whitespace'])

    def test_changed_owner_or_deadline_is_not_treated_as_equivalent(self):
        for old, new in [('Anna', 'Anne'), ('Donnerstag', 'Freitag'), ('prüft', 'prüft nicht')]:
            with self.subTest(new=new), self.assertRaises(AssertionError):
                self.check(self.text.replace(old, new))

    def test_missing_duplicate_or_wrongly_grouped_card_fails(self):
        for changed in (self.text.replace('text-2', 'text-1'), self.text.replace('in frame frame-1', 'in frame frame-2', 1),
                        self.text.rsplit('\n- [text-2]', 1)[0], self.text + self.text.split('\nNodes:\n')[1]):
            with self.subTest(changed=changed), self.assertRaises(AssertionError): self.check(changed)

    def test_wrong_title_or_truncated_content_fails(self):
        for changed in (self.text.replace('Ziel und Zeitraum', 'Was lief gut?'), self.text.replace('Ben versendet die Agenda bis Freitag.', '…')):
            with self.subTest(changed=changed), self.assertRaises(AssertionError): self.check(changed)

    def test_unexpected_contract_is_not_silently_accepted(self):
        with self.assertRaises(AssertionError): verify_readback({'nodes': []}, self.titles, self.sections)

    def test_spoken_fact_check_ignores_hyphen_but_keeps_proper_name(self):
        self.assertTrue(contains_facts('Team-Workshop Alpha', ['teamworkshop', 'alpha']))
        self.assertFalse(contains_facts('Team-Workshop Nordstrand', ['teamworkshop', 'nordstern']))


if __name__ == '__main__': unittest.main()
