import hashlib
import sys
import types
import unittest
from unittest.mock import Mock,patch
from services.nfc_reader import sample, select_reader

class NoCard(Exception):pass

class ReaderTests(unittest.TestCase):
    def run_sample(self,connect_error=None,post_disconnect=False,response=([1,2,3,4],0x90,0)):
        c=Mock();c.connect.side_effect=connect_error;c.transmit.return_value=response
        r=Mock();r.createConnection.return_value=c
        enumerator=Mock(side_effect=[[r],[]] if post_disconnect else lambda:[r])
        modules={'smartcard':types.ModuleType('smartcard'),'smartcard.System':types.ModuleType('smartcard.System'),'smartcard.Exceptions':types.ModuleType('smartcard.Exceptions')}
        modules['smartcard.System'].readers=enumerator;modules['smartcard.Exceptions'].NoCardException=NoCard
        with patch.dict(sys.modules,modules):value=sample()
        c.disconnect.assert_called_once()
        return value
    def test_no_card_is_empty_only_if_same_reader_remains(self):
        self.assertEqual(self.run_sample(NoCard())['state'],'absent')
        self.assertEqual(self.run_sample(NoCard(),True)['state'],'error')
    def test_uid_is_hashed_before_leaving_worker(self):
        self.assertEqual(self.run_sample(),{'state':'present','tag':hashlib.sha256(bytes([1,2,3,4])).hexdigest()})
    def test_unsupported_command_never_looks_like_removal(self):
        self.assertEqual(self.run_sample(response=([],0x6a,0x81))['state'],'error')
    def test_transport_exception_is_not_swallowed_as_no_card(self):
        with self.assertRaises(OSError):self.run_sample(OSError('USB gone'))

class NamedReader:
    def __init__(self, name, connection=None):self.name,self.connection=name,connection
    def __str__(self):return self.name
    def createConnection(self):return self.connection


class DualInterfaceTests(unittest.TestCase):
    def test_rocketek_contactless_selection_is_independent_of_enumeration_order(self):
        contact=NamedReader('Alcor Link AK9567 00 00')
        nfc=NamedReader('Alcor Link AK9567 [Contactless Card Reader] 01 00')
        self.assertIs(select_reader([contact,nfc]),nfc)
        self.assertIs(select_reader([nfc,contact]),nfc)
        self.assertIs(select_reader([contact]),contact)  # existing single-reader support
        self.assertIsNone(select_reader([]))
        self.assertIsNone(select_reader([contact,NamedReader('Unknown NFC reader')]))
        self.assertIsNone(select_reader([nfc,NamedReader('Second Contactless Card Reader')]))

    def test_contact_slot_is_never_opened_and_usb_loss_never_becomes_removal(self):
        for changed in (False,True):
            contact_connection=Mock();connection=Mock();connection.connect.side_effect=NoCard()
            contact=NamedReader('Alcor Link AK9567 00 00',contact_connection)
            nfc=NamedReader('Alcor Link AK9567 [Contactless Card Reader] 01 00',connection)
            modules={'smartcard.System':types.ModuleType('smartcard.System'),'smartcard.Exceptions':types.ModuleType('smartcard.Exceptions'),'smartcard':types.ModuleType('smartcard')}
            modules['smartcard.System'].readers=Mock(side_effect=[[contact,nfc],[contact] if changed else [nfc,contact]])
            modules['smartcard.Exceptions'].NoCardException=NoCard
            with patch.dict(sys.modules,modules):value=sample()
            self.assertEqual(value['state'],'error' if changed else 'absent')
            contact_connection.connect.assert_not_called();connection.disconnect.assert_called_once()

    def test_polling_does_not_fall_back_to_contact_slot_when_nfc_interface_disappears(self):
        connection=Mock();connection.connect.side_effect=NoCard()
        contact_connection=Mock()
        contact=NamedReader('Alcor Link AK9567 00 00',contact_connection)
        nfc=NamedReader('Alcor Link AK9567 [Contactless Card Reader] 01 00',connection)
        modules={'smartcard.System':types.ModuleType('smartcard.System'),'smartcard.Exceptions':types.ModuleType('smartcard.Exceptions'),'smartcard':types.ModuleType('smartcard')}
        modules['smartcard.System'].readers=Mock(side_effect=[[contact,nfc],[contact,nfc],[contact]])
        modules['smartcard.Exceptions'].NoCardException=NoCard
        selection={}
        with patch.dict(sys.modules,modules):
            self.assertEqual(sample(selection)['state'],'absent')
            self.assertEqual(sample(selection)['state'],'error')
        contact_connection.connect.assert_not_called()

if __name__=='__main__':unittest.main()
