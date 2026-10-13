import asyncio
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
from services.bluetooth_audio import BluetoothAudio,audio_profiles,public_devices,make_agent

ADAPTER='/org/bluez/hci0';DEVICE=ADAPTER+'/dev_AA_BB_CC_DD_EE_FF'
class ProfileTests(unittest.TestCase):
    def test_only_exact_device_and_output_or_duplex_profiles(self):
        cards=[{'name':'card','properties':{'api.bluez5.address':'AA:BB:CC:DD:EE:FF'},'active_profile':'a2dp-sink','profiles':{'off':{},'a2dp-sink':{'description':'SBC','available':'yes'},'headset-head-unit':{'description':'HFP','available':'unknown'},'a2dp-source':{},'headset-head-unit-msbc':{'available':'no'}}}]
        run=lambda *a,**kw:SimpleNamespace(stdout=json.dumps(cards))
        self.assertIsNone(audio_profiles('other',run));p=audio_profiles('aa:bb:cc:dd:ee:ff',run)
        self.assertEqual([p['id'] for p in p['profiles']],['a2dp-sink','headset-head-unit'])
    def test_device_filter_and_audio_capability(self):
        o={DEVICE:{'org.bluez.Device1':{'Adapter':ADAPTER,'Alias':'Box','Address':'AA','Paired':True,'UUIDs':['0000110b-0000-1000-8000-00805f9b34fb']}},'other':{'org.bluez.Device1':{'Adapter':'other'}}}
        r=public_devices(o,ADAPTER);self.assertEqual(len(r),1);self.assertTrue(r[0]['audio']);self.assertFalse(r[0]['connected'])

class PairingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.b=BluetoothAudio(False);self.b.loop=asyncio.get_running_loop();self.b.adapter=ADAPTER
        self.b.update(supported=True,powered=True,devices=[{'id':DEVICE,'address':'AA'}]);self.b.call=AsyncMock(return_value=[]);self.b.refresh=AsyncMock();self.b.set_property=AsyncMock()
    async def asyncTearDown(self):
        self.b._cancel()
        if self.b.task:await asyncio.gather(self.b.task,return_exceptions=True)
    async def test_pairing_checks_code_before_trusting(self):
        async def call(path,interface,member,*a,**kw):
            if member=='Pair':await self.b.ask(DEVICE,'confirm','001234')
            return []
        self.b.call.side_effect=call
        self.b.action({'action':'pair','device':DEVICE});await asyncio.sleep(.01)
        prompt=self.b.public()['prompt'];self.assertEqual(prompt['code'],'001234');self.b.set_property.assert_not_awaited()
        self.b.reply({'id':prompt['id'],'accept':True});await self.b.task;await asyncio.sleep(0)
        self.b.set_property.assert_awaited_once_with(DEVICE,'org.bluez.Device1','Trusted','b',True);self.assertFalse(self.b.busy())
    async def test_rejected_or_unsolicited_pairing_never_trusted(self):
        from dbus_next import DBusError
        with self.assertRaises(DBusError):await self.b.ask(DEVICE,'authorize')
        async def call(path,interface,member,*a,**kw):
            if member=='Pair':await self.b.ask(DEVICE,'authorize')
            return []
        self.b.call.side_effect=call;self.b.action({'action':'pair','device':DEVICE});await asyncio.sleep(.01)
        p=self.b.public()['prompt'];self.b.reply({'id':p['id'],'accept':False});await self.b.task
        self.b.set_property.assert_not_awaited();self.assertFalse(self.b.busy())
    async def test_scan_cancel_releases_owned_discovery_and_lock(self):
        self.b.action({'action':'scan'});await asyncio.sleep(.01);self.assertTrue(self.b.busy());self.b.action({'action':'cancel'});await asyncio.sleep(.01)
        self.assertFalse(self.b.busy());self.assertIn('StopDiscovery',[c.args[2] for c in self.b.call.await_args_list])
    async def test_immediate_cancel_before_operation_starts_unlocks(self):
        self.b.action({'action':'scan'});self.b.action({'action':'cancel'});await asyncio.sleep(.01);self.assertFalse(self.b.busy())
    async def test_cancel_connect_explicitly_disconnects_before_unlock(self):
        async def call(path,interface,member,*a,**kw):
            if member=='Connect':await asyncio.sleep(100)
            return []
        self.b.call.side_effect=call;self.b.action({'action':'connect','device':DEVICE});await asyncio.sleep(.01)
        self.b.action({'action':'cancel'});await asyncio.sleep(.01)
        self.assertIn('Disconnect',[c.args[2] for c in self.b.call.await_args_list]);self.assertFalse(self.b.busy())

    async def test_selection_during_scan_transfers_reservation(self):
        waiter=asyncio.Event()
        async def call(path,interface,member,*a,**kw):
            if member=='Connect':await waiter.wait()
            return []
        self.b.call.side_effect=call;self.b.action({'action':'scan'});await asyncio.sleep(.01);self.b.action({'action':'connect','device':DEVICE});await asyncio.sleep(.01)
        self.assertTrue(self.b.busy());self.assertEqual(self.b.public()['operation'],'connect');waiter.set();await self.b.task;await asyncio.sleep(0);self.assertFalse(self.b.busy())
    async def test_stale_and_invalid_confirmation_and_device_rejected(self):
        for body in [{'action':'forget','device':DEVICE},{'action':'connect','device':'/org/bluez/other'},{'action':'power','powered':'true'},{'action':'reply','id':'stale','accept':True}]:
            with self.assertRaises(ValueError):self.b.action(body)
    async def test_passkey_validation_keeps_prompt_open(self):
        self.b.target=DEVICE;self.b.update(operation='pair');task=asyncio.create_task(self.b.ask(DEVICE,'passkey'));await asyncio.sleep(0);p=self.b.public()['prompt']
        with self.assertRaises(ValueError):self.b.reply({'id':p['id'],'accept':True,'value':'invalid'})
        self.b.reply({'id':p['id'],'accept':True,'value':'001234'});self.assertEqual(await task,'001234')
    async def test_agent_exports_all_required_methods(self):
        a=make_agent(self.b);names={m.name for m in a.introspect().methods};self.assertTrue({'RequestPinCode','RequestPasskey','RequestConfirmation','Cancel','AuthorizeService'}<=names)
