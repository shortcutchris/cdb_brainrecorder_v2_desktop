import hashlib
import sys
import types
import unittest
from unittest.mock import Mock,patch
from services.nfc_reader import sample

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

if __name__=='__main__':unittest.main()
