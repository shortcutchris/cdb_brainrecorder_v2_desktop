import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from services.respeaker_leds import ReSpeakerLeds, UsbRing, selected_usb


class Ring:
    serial='test-array'
    def __init__(self):self.values={'effect':4,'color':8256};self.mute=False;self.calls=[];self.closed=False
    def snapshot(self):return dict(self.values)
    def show(self,effect,color):self.calls.append((effect,color));self.values={'effect':effect,'color':color}
    def restore(self,values):self.show(values['effect'],values['color'])
    def hardware_muted(self):return self.mute
    def close(self):self.closed=True


class LedTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.ring=Ring();self.state={'device':'plughw:CARD=Array,DEV=0','recording':{},'probe':False}
        self.service=ReSpeakerLeds(self.tmp.name,lambda:self.state,factory=lambda _:self.ring,start=False)
    def tearDown(self):self.service.close();self.tmp.cleanup()
    def test_all_states_and_mute_over_pause_then_idle_restore(self):
        s=self.service;s.tick(0);self.assertEqual(self.ring.values,{'effect':4,'color':8256})
        self.state['recording']={'id':'one'};s.tick(1);self.assertEqual(self.ring.values,{'effect':3,'color':0x2266ff})
        self.state['recording']['paused']=True;s.tick(2);self.assertEqual(self.ring.values['color'],0xe0a000)
        self.state['recording']['muted']=True;s.tick(3);self.assertEqual(self.ring.values,{'effect':3,'color':0xcc2424})
        s.tick(3.5);self.assertEqual(self.ring.values['effect'],0)
        self.state['recording']={};s.tick(4);self.assertEqual(self.ring.values,{'effect':4,'color':8256})
    def test_hardware_mute_never_overridden_even_close(self):
        self.service.tick(0);self.ring.mute=True;before=list(self.ring.calls)
        self.state['recording']={'id':'one'};self.service.tick(1)
        self.assertTrue(self.service.public()['hardware_muted']);self.service.close()
        self.assertEqual(self.ring.calls,before);self.assertTrue(self.service.path.exists())
    def test_unmute_reapplies_current_state(self):
        self.state['recording']={'id':'one'};self.service.tick(0);self.ring.mute=True;self.service.tick(1)
        self.ring.mute=False;self.ring.values={'effect':4,'color':8256};self.service.tick(2)
        self.assertEqual(self.ring.values['color'],0x2266ff)
    def test_probe_is_blue_and_other_mic_restores(self):
        self.state['probe']=True;self.service.tick(0);self.assertEqual(self.ring.values['color'],0x2266ff)
        self.service.factory=lambda _:None;self.state['device']='default';self.service.tick(1)
        self.assertEqual(self.ring.values,{'effect':4,'color':8256});self.assertFalse(self.service.public()['connected'])
    def test_usb_error_then_reconnect_restores_original_not_recording_color(self):
        self.state['recording']={'id':'one'};self.service.tick(0)
        self.ring.hardware_muted=Mock(side_effect=OSError('unplugged'));self.service.tick(1)
        self.assertEqual(self.service.public()['state'],'error')
        self.ring.hardware_muted=lambda:False;self.state['recording']={};self.service.tick(4)
        self.assertEqual(self.ring.values,{'effect':4,'color':8256})
    def test_process_restart_recovers_persistent_pre_app_state(self):
        self.service.path.write_text(json.dumps({'serial':'test-array','values':{'effect':2,'color':77}}))
        self.ring.values={'effect':3,'color':0xcc2424};self.service.tick(0)
        self.assertEqual(self.ring.values,{'effect':2,'color':77});self.service.close();self.assertFalse(self.service.path.exists())
    def test_missing_optional_usb_is_nonfatal(self):
        self.service.factory=Mock(side_effect=ImportError('pyusb'));self.service.tick(0)
        self.assertEqual(self.service.public()['state'],'error');self.assertEqual(self.state['recording'],{})
    def test_identical_state_does_not_rewrite_usb(self):
        self.service.tick(0);self.service.tick(1);self.assertEqual(len(self.ring.calls),1)
    def test_protocol_read_and_write_are_limited_and_correct(self):
        device=Mock(serial_number='test');device.ctrl_transfer.return_value=bytes([0,0,1,0,1,0]);ring=UsbRing(device)
        self.assertTrue(ring.hardware_muted());device.ctrl_transfer.assert_called_with(0xc0,0,128,20,6,timeout=250)
        ring.show(3,0x2266ff);self.assertEqual(device.ctrl_transfer.call_args_list[-2].args,(0x40,0,16,20,b'\xff\x66\x22\x00'))
        device.ctrl_transfer.return_value=b'\x40';self.assertRaises(OSError,ring.read,12,1)
    def test_selected_device_does_not_match_default_or_wrong_usb(self):
        self.assertIsNone(selected_usb('default',Path(self.tmp.name)))
        root=Path(self.tmp.name);card=root/'card2';card.mkdir();(card/'id').write_text('Array')
        usb=root/'usb';usb.mkdir();interface=usb/'3-1:1.0';interface.mkdir();(card/'device').symlink_to(interface)
        for name,value in {'idVendor':'2886','idProduct':'001a','busnum':'3','devnum':'9'}.items():(usb/name).write_text(value)
        self.assertEqual(selected_usb('plughw:CARD=Array,DEV=0',root),(3,9))
        self.assertIsNone(selected_usb('plughw:CARD=Else,DEV=0',root))
        (usb/'idVendor').write_text('ffff');self.assertIsNone(selected_usb('plughw:CARD=Array,DEV=0',root))
