"""BlueZ pairing owned by this app, with explicit touch confirmation and timeouts."""
import asyncio
import copy
import json
import re
import subprocess
import threading
import uuid

AUDIO_UUIDS = {'00001108','0000110a','0000110b','0000111e','0000111f'}


def audio_profiles(address, runner=subprocess.run):
    try:
        cards=json.loads(runner(['pactl','-f','json','list','cards'],capture_output=True,text=True,check=True,timeout=4).stdout)
    except (OSError,ValueError,subprocess.SubprocessError):return None
    for card in cards:
        props=card.get('properties',{})
        if str(props.get('api.bluez5.address',props.get('device.string',''))).upper()!=address.upper():continue
        profiles=[]
        for name,p in card.get('profiles',{}).items():
            if p.get('available') in ('no',False):continue
            if name.startswith('a2dp-sink'):label='Musik · Lautsprecher'
            elif name.startswith('headset-head-unit'):label='Gespräch · Mikrofon + Lautsprecher'
            else:continue
            profiles.append({'id':name,'label':label+' · '+p.get('description',name)})
        endpoints={}
        for kind in ('sinks','sources'):
            try:
                entries=json.loads(runner(['pactl','-f','json','list',kind],capture_output=True,text=True,check=True,timeout=4).stdout)
                endpoints[kind]=[{'id':e['name'],'label':e.get('description',e['name'])} for e in entries
                    if (str(e.get('properties',{}).get('api.bluez5.address',e.get('properties',{}).get('device.string',''))).upper()==address.upper()
                        or (card.get('index') is not None and e.get('card')==card['index']))
                    and (kind!='sources' or not e['name'].endswith('.monitor'))]
            except (OSError,ValueError,subprocess.SubprocessError):endpoints[kind]=[]
        return {'card':card['name'],'active':card.get('active_profile',''),'profiles':profiles,**endpoints}
    return None


def public_devices(objects,adapter):
    rows=[]
    for path,interfaces in objects.items():
        d=interfaces.get('org.bluez.Device1')
        if not d or d.get('Adapter')!=adapter:continue
        audio=any(u[:8].lower() in AUDIO_UUIDS for u in d.get('UUIDs',[])) or d.get('Icon','').startswith('audio')
        # Unknown devices remain visible while discovering: UUIDs often arrive after pairing.
        rows.append({'id':path,'name':d.get('Alias') or d.get('Name') or d.get('Address','Unbekannt'),
            'address':d.get('Address',''),'paired':bool(d.get('Paired')),'connected':bool(d.get('Connected')),
            'audio':audio,'rssi':d.get('RSSI'),'profile':audio_profiles(d.get('Address','')) if d.get('Connected') and audio else None})
    return sorted(rows,key=lambda d:(not d['connected'],not d['paired'],d['name'].lower()))


class BluetoothAudio:
    def __init__(self,enabled=True):
        self.enabled=enabled;self.lock=threading.RLock();self.loop=None;self.thread=None;self.bus=None
        self.objects={};self.adapter=None;self.task=None;self.target=None;self.prompt_future=None;self.closing=False
        self.data={'supported':False,'powered':False,'adapter':'','devices':[],'busy':False,'operation':'',
                   'message':'Bluetooth wird beim Öffnen geprüft.','prompt':None}

    def start(self):
        with self.lock:
            if self.thread or not self.enabled or self.closing:return
            self.thread=threading.Thread(target=self._run,daemon=True);self.thread.start()

    def public(self):
        with self.lock:return copy.deepcopy(self.data)

    def busy(self):
        with self.lock:return self.data['busy']

    def update(self,**values):
        with self.lock:self.data.update(values)

    def _run(self):
        self.loop=asyncio.new_event_loop();asyncio.set_event_loop(self.loop)
        try:self.loop.run_until_complete(self._main())
        except Exception:self.update(supported=False,message='Bluetooth-Dienst nicht erreichbar. Gerät & Diagnose prüfen.')
        finally:
            if self.bus:self.bus.disconnect()
            self.update(busy=False,operation='',prompt=None)
            self.loop.close()
            with self.lock:self.thread=None;self.loop=None

    async def call(self,path,interface,member,signature='',body=None,timeout=12):
        from dbus_next import Message,MessageType
        reply=await asyncio.wait_for(self.bus.call(Message(destination='org.bluez',path=path,interface=interface,
            member=member,signature=signature,body=body or [])),timeout)
        if reply.message_type==MessageType.ERROR:raise ValueError(reply.error_name+': '+str(reply.body[0] if reply.body else ''))
        return reply.body

    async def set_property(self,path,interface,key,kind,value):
        from dbus_next import Variant
        await self.call(path,'org.freedesktop.DBus.Properties','Set','ssv',[interface,key,Variant(kind,value)])

    async def refresh(self):
        def unwrap(v):
            if hasattr(v,'value'):return unwrap(v.value)
            if isinstance(v,dict):return {k:unwrap(x) for k,x in v.items()}
            if isinstance(v,list):return [unwrap(x) for x in v]
            return v
        objects=unwrap((await self.call('/','org.freedesktop.DBus.ObjectManager','GetManagedObjects'))[0])
        adapters=sorted(p for p,i in objects.items() if 'org.bluez.Adapter1' in i)
        self.objects=objects
        if self.adapter not in adapters:self.adapter=adapters[0] if adapters else None
        a=objects.get(self.adapter,{}).get('org.bluez.Adapter1',{})
        rows=await asyncio.to_thread(public_devices,objects,self.adapter)
        self.update(supported=bool(a),powered=bool(a.get('Powered')),adapter=a.get('Alias',''),devices=rows)

    async def _main(self):
        from dbus_next.aio import MessageBus
        from dbus_next.constants import BusType
        self.bus=await MessageBus(bus_type=BusType.SYSTEM).connect()
        self.bus.export('/com/cdb/RecorderAgent',make_agent(self))
        await self.call('/org/bluez','org.bluez.AgentManager1','RegisterAgent','os',['/com/cdb/RecorderAgent','KeyboardDisplay'])
        # Never become the default agent or accept unsolicited pairing requests.
        await self.refresh();self.update(message='Gerät in den Kopplungsmodus versetzen und suchen.')
        while not self.closing:
            await asyncio.sleep(2)
            try:await self.refresh()
            except Exception:self.update(supported=False,message='Bluetooth-Verbindung unterbrochen.')
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task,return_exceptions=True)
        try:await self.call('/org/bluez','org.bluez.AgentManager1','UnregisterAgent','o',['/com/cdb/RecorderAgent'],timeout=3)
        except Exception:pass

    def action(self,body):
        operation=body.get('action')
        if operation=='reply':return self.reply(body)
        if operation=='cancel':
            if self.loop and not self.loop.is_closed():self.loop.call_soon_threadsafe(self._cancel)
            return self.public()
        if operation not in ('scan','power','pair','connect','disconnect','forget','profile'):raise ValueError('Unbekannte Bluetooth-Aktion.')
        with self.lock:
            if self.closing or not self.loop or not self.data['supported']:raise ValueError('Bluetooth ist noch nicht bereit. Aktualisieren.')
            if self.data['busy'] and self.data['operation']!='scan':raise ValueError('Bluetooth-Aktion läuft. Bitte warten oder abbrechen.')
            device=body.get('device')
            if operation not in ('scan','power') and not any(d['id']==device for d in self.data['devices']):raise ValueError('Gerät nicht mehr vorhanden. Erneut suchen.')
            if operation=='power' and type(body.get('powered')) is not bool:raise ValueError('Ungültiger Bluetooth-Zustand.')
            if operation=='forget' and body.get('confirmed') is not True:raise ValueError('Entfernen der Kopplung zuerst bestätigen.')
            self.data.update(busy=True,operation=operation,prompt=None,message={'scan':'Suche läuft · maximal 60 Sekunden','pair':'Kopplung läuft …','connect':'Verbindung wird aufgebaut …','disconnect':'Verbindung wird getrennt …','forget':'Kopplung wird entfernt …','profile':'Audiomodus wird gewechselt …','power':'Bluetooth wird umgeschaltet …'}[operation])
            self.loop.call_soon_threadsafe(self._schedule,operation,dict(body))
        return self.public()

    def _schedule(self,operation,body):
        previous=self.task
        async def queued():
            if previous:
                previous.cancel();await asyncio.gather(previous,return_exceptions=True)
            await self._operate(operation,body)
        self.task=asyncio.create_task(queued())
        def finished(task):
            if task is self.task:self.update(busy=False,operation='',prompt=None)
        self.task.add_done_callback(finished)

    def _cancel(self):
        if self.prompt_future and not self.prompt_future.done():self.prompt_future.cancel()
        if self.task:self.task.cancel()

    async def _operate(self,operation,body):
        device=body.get('device');self.target=device;cancelled=False
        try:
            if operation=='power':await self.set_property(self.adapter,'org.bluez.Adapter1','Powered','b',body['powered'])
            elif operation=='scan':
                if not self.data['powered']:raise ValueError('org.bluez.Error.NotReady')
                await self.call(self.adapter,'org.bluez.Adapter1','StartDiscovery')
                await asyncio.sleep(60)
            elif operation=='pair':
                await self.call(device,'org.bluez.Device1','Pair',timeout=90)
                await self.set_property(device,'org.bluez.Device1','Trusted','b',True)
                await self.call(device,'org.bluez.Device1','Connect',timeout=25)
            elif operation in ('connect','disconnect'):await self.call(device,'org.bluez.Device1','Connect' if operation=='connect' else 'Disconnect',timeout=25)
            elif operation=='forget':await self.call(self.adapter,'org.bluez.Adapter1','RemoveDevice','o',[device])
            elif operation=='profile':
                d=next(d for d in self.data['devices'] if d['id']==device)
                profile=await asyncio.to_thread(audio_profiles,d['address'])
                if not profile or not any(p['id']==body.get('profile') for p in profile['profiles']):raise ValueError('Audiomodus ist nicht verfügbar.')
                await asyncio.to_thread(subprocess.run,['pactl','set-card-profile',profile['card'],body['profile']],check=True,capture_output=True,timeout=12)
            await self.refresh()
            if operation in ('pair','connect','profile'):
                d=next((d for d in self.data['devices'] if d['id']==device),{})
                profile=d.get('profile') or {}
                message=('Audio bereit. Unten den gewünschten Ein- oder Ausgang auswählen.' if d.get('connected') and (profile.get('sinks') or profile.get('sources'))
                    else 'Bluetooth verbunden. Audio noch nicht verfügbar; Status wird weiter geprüft.' if d.get('connected')
                    else 'Gekoppelt, aber nicht verbunden. Gerät einschalten und erneut verbinden.' if d.get('paired')
                    else 'Keine Verbindung. Gerät in den Kopplungsmodus versetzen und erneut versuchen.')
            else:message={'scan':'Suche beendet.','disconnect':'Verbindung getrennt. Kopplung bleibt gespeichert.',
                'forget':'Kopplung entfernt.','power':'Bluetooth eingeschaltet.' if body.get('powered') else 'Bluetooth ausgeschaltet.'}[operation]
            self.update(message=message)
        except asyncio.CancelledError:
            cancelled=True;self.update(message='Bluetooth-Aktion abgebrochen.')
        except Exception as error:
            cancelled=True
            name=str(error)
            message='Bluetooth-Aktion fehlgeschlagen. Gerät einschalten, Kopplungsmodus prüfen und erneut versuchen.'
            if 'br-connection' in name or 'ConnectionAttemptFailed' in name:message='Keine Audioverbindung. Handyverbindung trennen und erneut verbinden. Falls das nicht hilft: Kopplung entfernen und neu koppeln.'
            elif 'Authentication' in name:message='Kopplung nicht bestätigt oder Zeit abgelaufen. Bitte erneut koppeln.'
            elif 'NotReady' in name:message='Bluetooth zuerst einschalten. Falls nötig, Funkfreigabe am Pi prüfen.'
            elif 'NotAuthorized' in name or 'AccessDenied' in name:message='Der Pi-Benutzer darf Bluetooth nicht verwalten. Geräteberechtigungen prüfen.'
            elif operation=='profile':message='Audiomodus konnte nicht gewechselt werden. Gerät neu verbinden.'
            self.update(message=message)
        finally:
            if operation=='scan':
                try:await self.call(self.adapter,'org.bluez.Adapter1','StopDiscovery',timeout=3)
                except Exception:pass
            if operation=='pair':
                try:await self.call(device,'org.bluez.Device1','CancelPairing',timeout=3)
                except Exception:pass
            if cancelled and operation in ('pair','connect'):
                try:await self.call(device,'org.bluez.Device1','Disconnect',timeout=4)
                except Exception:pass
            self.target=None;self.prompt_future=None
            try:await self.refresh()
            except Exception:pass
            # A successor may already own the reservation while this task cleans up.
            if asyncio.current_task() is self.task:self.update(busy=False,operation='',prompt=None)

    async def ask(self,device,kind,code=''):
        from dbus_next import DBusError
        if device!=self.target or self.data['operation']!='pair':raise DBusError('org.bluez.Error.Rejected','Keine angeforderte Kopplung')
        token=uuid.uuid4().hex;self.prompt_future=asyncio.get_running_loop().create_future()
        self.update(prompt={'id':token,'kind':kind,'code':code,'device':device})
        try:
            result=await asyncio.wait_for(self.prompt_future,60)
            if not result['accept']:raise DBusError('org.bluez.Error.Rejected','Abgelehnt')
            return result.get('value','')
        except (asyncio.TimeoutError,asyncio.CancelledError):raise DBusError('org.bluez.Error.Canceled','Abgebrochen') from None
        finally:self.update(prompt=None)

    def reply(self,body):
        with self.lock:
            prompt=self.data['prompt']
            if not prompt or body.get('id')!=prompt['id'] or type(body.get('accept')) is not bool:raise ValueError('Diese Kopplungsfrage ist nicht mehr aktuell.')
            value=body.get('value','')
            if body['accept'] and prompt['kind']=='pin' and (not isinstance(value,str) or not re.fullmatch(r'[ -~]{1,16}',value)):raise ValueError('PIN mit 1 bis 16 Zeichen eingeben.')
            if body['accept'] and prompt['kind']=='passkey' and (not isinstance(value,str) or not re.fullmatch(r'\d{1,6}',value)):raise ValueError('Code mit bis zu sechs Ziffern eingeben.')
            future=self.prompt_future
            def resolve():
                if future and not future.done():future.set_result(dict(body))
            self.loop.call_soon_threadsafe(resolve)
        return self.public()

    def close(self):
        self.closing=True
        if self.loop and not self.loop.is_closed():self.loop.call_soon_threadsafe(self._cancel)
        if self.thread:self.thread.join(timeout=8)


def make_agent(owner):
    from dbus_next.service import ServiceInterface,method
    from dbus_next import DBusError
    class Agent(ServiceInterface):
        def __init__(self):super().__init__('org.bluez.Agent1')
        @method()
        def Release(self):owner._cancel()
        @method()
        def Cancel(self):
            if owner.prompt_future and not owner.prompt_future.done():owner.prompt_future.cancel()
        @method()
        async def RequestConfirmation(self,device:'o',passkey:'u'):await owner.ask(device,'confirm',f'{passkey:06d}')
        @method()
        async def RequestAuthorization(self,device:'o'):await owner.ask(device,'authorize')
        @method()
        async def RequestPinCode(self,device:'o')->'s':return await owner.ask(device,'pin')
        @method()
        async def RequestPasskey(self,device:'o')->'u':return int(await owner.ask(device,'passkey'))
        @method()
        def DisplayPinCode(self,device:'o',pincode:'s'):self.display(device,pincode)
        @method()
        def DisplayPasskey(self,device:'o',passkey:'u',entered:'q'):self.display(device,f'{passkey:06d}')
        def display(self,device,code):
            if device!=owner.target:raise DBusError('org.bluez.Error.Rejected','Keine angeforderte Kopplung')
            owner.update(prompt={'id':'display','kind':'display','code':code,'device':device})
        @method()
        def AuthorizeService(self,device:'o',service:'s'):
            if device!=owner.target or service[:8].lower() not in AUDIO_UUIDS|{'0000110c','0000110e','0000110f'}:
                raise DBusError('org.bluez.Error.Rejected','Nicht angeforderter Audiodienst')
    return Agent()
