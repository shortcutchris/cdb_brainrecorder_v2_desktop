"""CDB Voice One broker with native Python audio on the Pi.

The browser never receives a Microsoft token or accesses audio hardware. A short
owner-only lease reserves Pi audio; lost tabs, stale bindings and failed starts release it.
"""
import json
import hashlib
import os
from pathlib import Path
import re
import secrets
import threading
import time
import urllib.request
import uuid

from meeting_recorder.core import atomic_write
from services.live_feedback import SearchActivity
from services.http_connection import HTTPSHandler
from services.cdb_integration import CdbFailure, USER_AGENT, UUID

BASE = '/api/v1/tqs/voice-live'
HANDLE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
# Whole user utterances only: recognize natural imperatives, never echoed
# assistant promises ("ich beende ...") or a quoted/negated command.
END_COMMAND = re.compile(
    r'(?:(?:okay|ok|danke)\s+)?(?:bitte\s+)?(?:'
    r'(?:das\s+)?(?:gespräch|unterhaltung)(?:\s+(?:jetzt|bitte))?\s+beenden'
    r'|beende(?:\s+bitte)?\s+(?:das\s+gespräch|die\s+unterhaltung)(?:\s+jetzt)?'
    r'|(?:jetzt\s+)?(?:beenden|ende)'
    r'|das\s+war[’\']?s'
    r')(?:\s+bitte)?'
)

ACTIVE = {'connecting', 'listening', 'thinking', 'speaking', 'reconnecting', 'closing'}


class LiveConversation:
    def __init__(self, cdb, root, clock=time.monotonic, events=None, audio_config=None, audio_factory=None):
        self.cdb = cdb
        self.audio_config = audio_config
        self.audio_factory = audio_factory
        self.device_executor = None
        self.device_key = None
        self.device_tools = False
        self.native = None
        self.root = Path(root) / 'live'
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.lock = threading.RLock()
        self.searches=SearchActivity(clock)
        self.search_sound=True
        try:
            pref=json.loads((self.root/'preferences.json').read_text())
            if type(pref.get('search_sound')) is bool:self.search_sound=pref['search_sound']
        except (OSError,ValueError):pass
        self.clock = clock
        self.event_reader = events or self._read_events
        self.stop = threading.Event()
        self.state = 'idle'
        self.error = ''
        self.end_reason = ''
        self.startup_stage = ''
        self.startup_at = 0
        self.lease = None
        self.owner_kind = 'browser'
        self.handle = None
        self.answer = None
        self.binding = None
        self.generation = 0
        self.restored_binding = None
        self.transcript_turns = {}
        self.seen_transcripts = set()
        self.history = []
        self.areas = []
        self.muted = False
        self.deadline = 0
        self.maximum = 0
        self.last_heartbeat = 0
        self.heartbeat_seconds = 15
        self.finished = threading.Event()
        self.finished.set()
        self.watch = threading.Thread(target=self._watch, daemon=True)
        self.watch.start()

    def _binding(self):
        s = self.cdb.session()
        return {'server': s['server'], **{k: s['identity'][k] for k in ('user_id', 'client_id')}}

    def busy(self):
        with self.lock:
            return self.state in ACTIVE

    def public(self):
        with self.lock:
            if self.binding and self.cdb.generation != getattr(self, 'account_generation', None):
                return {'state': 'closing' if self.state in ACTIVE else 'idle', 'busy': self.state in ACTIVE,
                        'error': '', 'muted': True, 'areas': [], 'history': [], 'model': 'CDB Voice One', 'started_at': None}
            return {'end_reason': self.end_reason, 'device_tools': self.device_tools, 'state': self.state, 'busy': self.state in ACTIVE, 'error': self.error,
                    'muted': self.muted, 'areas': list(self.areas), 'history': [dict(h) for h in self.history],
                    'model': 'CDB Voice One', 'started_at': getattr(self, 'started_at', None),
                    'owner_kind': self.owner_kind, 'transport': 'pi' if self.audio_config else 'browser', 'feedback':self.feedback(),
                    'audio_stats': self.native.stats() if self.native and hasattr(self.native, 'stats') else {}}

    def feedback(self):
        with self.lock:
            active=self.state in ACTIVE and self.state!='closing' and (not self.binding or self.cdb.generation==getattr(self,'account_generation',None))
            native=self.native.feedback() if active and self.native and hasattr(self.native,'feedback') else {}
            search=self.searches.public() if active else {'brain':0,'web':0,'failed':False}
            # Brain lifecycle is mirrored into native playback; count it only here.
            search['web']+=native.get('search',{}).get('web',0)
            search['failed']=search['failed'] or native.get('search',{}).get('failed',False)
            return {'state':self.state,'active':active,'muted':self.muted,'search':search,
                    'startup':{'stage':self.startup_stage,'seconds':max(0,int(self.clock()-self.startup_at))} if self.state=='connecting' else None,
                    'input':native.get('input',{'bars':[0]*16,'active':False}) if not self.muted else {'bars':[0]*16,'active':False},
                    'output':native.get('output',{'bars':[0]*16,'active':False}),
                    'search_sound':self.search_sound,'search_audio':native.get('search_audio',{'playing':False}),
                    'web_events':native.get('web_events',0)}

    def preferences(self, enabled, lease=None):
        if type(enabled) is not bool:raise ValueError('Ungültige Suchton-Einstellung.')
        with self.lock:
            if self.state in ACTIVE:self._owner(lease)
            atomic_write(self.root/'preferences.json',json.dumps({'search_sound':enabled}))
            self.search_sound=enabled
            if self.native and hasattr(self.native,'set_search_sound'):self.native.set_search_sound(enabled)
            return self.feedback()

    @staticmethod
    def _selection_key(binding):
        return hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()

    def remember_areas(self, area_ids, account_key):
        if not isinstance(area_ids, list) or len(area_ids) > 8 or any(not isinstance(x, str) or not UUID.fullmatch(x) for x in area_ids) or len(set(area_ids)) != len(area_ids):
            raise ValueError('Ungültige Bereichsauswahl.')
        with self.lock:
            if self.state in ACTIVE: raise ValueError('Gespräch läuft. Auswahl ist gesperrt.')
            binding = self._binding()
            key = self._selection_key(binding)
            if not isinstance(account_key, str) or not secrets.compare_digest(key, account_key):
                raise ValueError('Brain-Konto hat sich geändert. Bereiche neu laden.')
            path = self.root / ('areas-' + key + '.json')
            atomic_write(path, json.dumps({'binding': binding, 'area_ids': area_ids}))
            os.chmod(path, 0o600)
            return {'saved': True}

    def _remembered_areas(self, binding, areas):
        try:
            path = self.root / ('areas-' + self._selection_key(binding) + '.json')
            if path.stat().st_size > 8192: return None
            row = json.loads(path.read_text())
            ids = row.get('area_ids')
            if row.get('binding') != binding or not isinstance(ids, list) or len(ids) > 8 or any(not isinstance(x, str) or not UUID.fullmatch(x) for x in ids): return None
            available = {a['id'] for a in areas}
            return list(dict.fromkeys(x for x in ids if x in available))
        except (OSError, ValueError, AttributeError): return None

    def setup(self):
        binding = self._binding()
        caps = self.cdb.call(BASE + '/capabilities', binding=binding)
        areas = self.cdb.areas(binding)
        self._restore(binding)
        maximum = caps.get('max_areas', 8)
        if not isinstance(maximum, int): maximum = 8
        return {'enabled': caps.get('enabled') is True, 'max_areas': min(8, max(1, maximum)),
                'areas': areas, 'default_area': self.cdb.public().get('destination'),
                'remembered_area_ids': self._remembered_areas(binding, areas), 'selection_account_key': self._selection_key(binding),
                'model': 'CDB Voice One', 'audio': self.audio_setup()}

    def audio_setup(self):
        from services.live_audio import NativeLiveAudio
        runtime = self.audio_factory is not None or NativeLiveAudio.available()
        try:
            if not self.audio_config: raise ValueError('Pi-Audio ist noch nicht eingerichtet.')
            config = self.audio_config()
            if not config.get('device') or not config.get('speaker'): raise ValueError('Mikrofon und Lautsprecher am Pi auswählen.')
            return {'available': runtime, 'runtime_available': runtime, 'transport': 'pi',
                    'microphone_label': config.get('microphone_label', config['device']),
                    'speaker_label': config.get('speaker_label', config['speaker']),
                    'message': '' if runtime else 'Native Live-Audio-Komponenten fehlen auf dem Pi.'}
        except ValueError as error:
            return {'available': False, 'runtime_available': runtime, 'transport': 'pi', 'message': str(error)}

    def _restore(self, binding):
        with self.lock:
            if self.state in ACTIVE: return
            if self.restored_binding == binding:
                self.account_generation = self.cdb.generation
                return
            self.restored_binding = dict(binding)
            self.history = []; self.areas = []; self.error = ''; self.state = 'idle'
            self.binding = dict(binding); self.account_generation = self.cdb.generation
            for path in sorted(self.root.glob('conversation-*.json'), reverse=True):
                try:
                    if path.stat().st_size > 64_000_000: continue
                    row = json.loads(path.read_text())
                    if row.get('binding') != binding: continue
                    self.history = row.get('history', [])
                    self.areas = row.get('areas', [])
                    self.started_at = row.get('started_at')
                    self.state = 'ended'; break
                except (ValueError, OSError): continue

    def reserve(self, area_ids, *, owner_kind="browser"):
        if not isinstance(area_ids, list) or not 1 <= len(area_ids) <= 8 or any(not isinstance(x, str) for x in area_ids) or len(set(area_ids)) != len(area_ids):
            raise ValueError('Bitte ein bis acht unterschiedliche Knowledge Areas wählen.')
        if any(not isinstance(x, str) or not UUID.fullmatch(x) for x in area_ids):
            raise ValueError('Ungültige Knowledge Area.')
        with self.lock:
            if self.state in ACTIVE:
                raise ValueError('Ein Gespräch läuft bereits.')
            self.binding = self._binding()
            self.account_generation = self.cdb.generation
            self.restored_binding = dict(self.binding)
            self.generation += 1
            self.owner_kind = owner_kind
            self.lease = secrets.token_urlsafe(32)
            self.state = 'connecting'
            self.startup_stage = 'Pi-Audio vorbereiten'
            self.startup_at = self.clock()
            self.error = ''
            self.end_reason = ''
            self.muted = False
            self.handle = self.answer = None
            self.history = []
            self.transcript_turns = {}
            self.seen_transcripts = set()
            self.searches=SearchActivity(self.clock)
            self.area_ids = list(area_ids)
            self.areas = []
            self.deadline = self.clock() + (120 if owner_kind == "device" else 25)
            self.maximum = self.clock() + 1200
            self.started_at = time.time()
            self.started_request = False
            self.finished.clear()
            return {'lease': self.lease}

    def _owner(self, lease):
        if not isinstance(lease, str) or not self.lease or not secrets.compare_digest(lease, self.lease):
            raise ValueError('Das Gespräch gehört zu einem anderen Browser oder ist beendet.')
        if self.state not in ACTIVE:
            raise ValueError('Das Gespräch ist bereits beendet.')

    def start(self, lease, sdp):
        if not isinstance(sdp, str) or not sdp.startswith('v=0') or len(sdp.encode()) > 65536:
            raise ValueError('Ungültiges Audio-Verbindungsangebot.')
        with self.lock:
            self._owner(lease)
            if self.started_request:
                raise ValueError('Gespräch wird bereits verbunden.')
            self.started_request = True
            generation = self.generation
        threading.Thread(target=self._start, args=(generation, sdp), daemon=True).start()
        return {'starting': True}

    def start_native(self, lease):
        from services.live_audio import NativeLiveAudio
        with self.lock:
            self._owner(lease)
            if self.started_request: raise ValueError('Gespräch wird bereits verbunden.')
            if not self.audio_config: raise ValueError('Pi-Audio ist noch nicht eingerichtet.')
            config = self.audio_config()
            if not config.get('device') or not config.get('speaker'):
                raise ValueError('Mikrofon und Lautsprecher am Pi auswählen.')
            factory = self.audio_factory or NativeLiveAudio
            if self.audio_factory is None and not NativeLiveAudio.available():
                raise ValueError('Native Live-Audio-Komponenten fehlen auf dem Pi.')
            generation = self.generation
            self.native = factory(config, lambda: self._native_failed(generation))
            if hasattr(self.native,'set_search_sound'):self.native.set_search_sound(self.search_sound)
            self.started_request = True
        threading.Thread(target=self._start_native, args=(generation, self.native), daemon=True).start()
        return {'starting': True, 'transport': 'pi'}

    def _native_failed(self, generation):
        with self.lock:
            if generation != self.generation or self.state not in ACTIVE: return
            self.error = 'Pi-Audio wurde unterbrochen. Mikrofon und Lautsprecher prüfen.'
        self.end()

    def _startup(self, generation, stage):
        with self.lock:
            if generation == self.generation and self.state == 'connecting':
                self.startup_stage = stage

    def _start_native(self, generation, native):
        try:
            with self.lock:
                if generation != self.generation: native.close(); return
            sdp = native.open()
            self._start(generation, sdp, native)
        except Exception:
            with self.lock:
                if generation == self.generation:
                    cancelled = self.state == 'closing'
                    self._finish('ended' if cancelled else 'error', '' if cancelled else 'Pi-Audio konnte nicht verbunden werden. Mikrofon und Lautsprecher prüfen.')

    def _start(self, generation, sdp, native=None):
        handle = None
        with self.lock:
            if generation != self.generation:
                if native: native.close()
                return
            binding = self.binding
            area_ids = list(self.area_ids)
        try:
            self._startup(generation, 'Brain-Freigabe prüfen')
            caps = self.cdb.call(BASE + '/capabilities', binding=binding)
            if caps.get('enabled') is not True:
                raise CdbFailure('Voice One ist in dieser Brain-Umgebung nicht freigeschaltet.')
            self._startup(generation, 'Wissensbereiche bestätigen')
            allowed = {a['id']: a for a in self.cdb.areas(binding)}
            maximum = caps.get('max_areas', 8)
            if not isinstance(maximum, int): maximum = 8
            if len(area_ids) > min(8, maximum) or any(a not in allowed for a in area_ids):
                raise CdbFailure('Mindestens eine Knowledge Area ist nicht mehr verfügbar.')
            with self.lock:
                if generation != self.generation: return
                if self.state == 'closing':
                    self._finish('ended'); return
            body = {'sdp':sdp,'area_ids':area_ids,'language':'de','client_request_id':str(uuid.uuid4())}
            device_key = secrets.token_urlsafe(32) if self.device_executor and caps.get('device_tools_v1') is True else None
            if device_key: body['device_tools']={'version':1,'key':device_key}
            self._startup(generation, 'Gespräch beim Brain starten')
            result = self.cdb.call(BASE + '/sessions', body, binding=binding)
            handle = result.get('session_handle')
            if not isinstance(handle, str) or not HANDLE.fullmatch(handle):
                raise CdbFailure('Brain hat keine gültige Gesprächssitzung bestätigt.')
            answer = result.get('sdp_answer')
            if not isinstance(answer, str) or not answer.startswith('v=0') or len(answer.encode()) > 65536:
                raise CdbFailure('Brain hat keine gültige Audioverbindung bestätigt.')
            with self.lock:
                stale = generation != self.generation or self.state == 'closing'
                if not stale:
                    self.device_key = device_key
                    self.device_tools = bool(device_key)
                    self.handle = handle
                    self.answer = answer
                    self.areas = [allowed[a] for a in area_ids]
                    self.heartbeat_seconds = min(30, max(5, int(caps.get('heartbeat_seconds', 15))))
                    self.maximum = min(self.maximum, self.clock() + min(1200, max(60, int(caps.get('max_session_seconds', 1200)))))
                    self.last_heartbeat = self.clock()
                    self.state = 'connecting' if native and hasattr(native,'wait_connected') else 'listening'
            if stale:
                self.cdb.call(BASE + '/sessions/' + handle + '/close', {}, binding=binding)
                with self.lock:
                    if generation == self.generation: self._finish('ended')
                return
            if native:
                self._startup(generation, 'Audioverbindung herstellen')
                native.answer(answer)
                if hasattr(native,'wait_connected'): native.wait_connected(15)
                with self.lock:
                    if generation == self.generation and self.state != 'closing': self.state = 'listening'
            with self.lock:
                if generation != self.generation or self.state == 'closing': return
            threading.Thread(target=self._events, args=(generation, handle, binding), daemon=True).start()
            if device_key:
                threading.Thread(target=self._device_loop,args=(generation,handle,binding),daemon=True).start()
        except Exception as error:
            # Only expose a locally defined authorization category, never provider details.
            denied = isinstance(error, CdbFailure) and str(error) == 'Keine Berechtigung für diese CDB-Aktion.'
            if handle:
                try: self.cdb.call(BASE + '/sessions/' + handle + '/close', {}, binding=binding)
                except Exception: pass
            with self.lock:
                if generation == self.generation:
                    cancelled = self.state == 'closing'
                    self._finish('ended' if cancelled else 'error', '' if cancelled else 'Brain hat diese Bereichsauswahl nicht freigegeben. Andere Bereiche wählen oder Berechtigung prüfen.' if denied else 'Gespräch konnte nicht verbunden werden. Brain-Verbindung und Live-Freigabe prüfen.')

    def status(self, lease):
        with self.lock:
            self._owner(lease)
            return {'state': self.state, 'sdp_answer': self.answer, 'muted': self.muted}

    def pulse(self, lease):
        with self.lock:
            self._owner(lease)
            self.deadline = self.clock() + 25
            return {'ok': True}

    def mute(self, lease, muted):
        if type(muted) is not bool: raise ValueError('Stumm muss ein Wahrheitswert sein.')
        with self.lock:
            self._owner(lease)
            if self.native: self.native.mute(muted)
            self.muted = muted
            return {'muted': muted}

    def end(self, lease=None):
        with self.lock:
            if lease is not None: self._owner(lease)
            if self.state not in ACTIVE: return {'closed': True}
            if self.state == 'closing': return {'closing': True}
            self.state = 'closing'
            if self.native:
                try: self.native.close()
                except Exception: pass
            generation, handle, binding = self.generation, self.handle, self.binding
            if self.started_request and handle is None: return {'closing': True}
        threading.Thread(target=self._end, args=(generation, handle, binding), daemon=True).start()
        return {'closing': True}

    def _end(self, generation, handle, binding):
        try:
            if handle: self.cdb.call(BASE + '/sessions/' + handle + '/close', {}, binding=binding)
        except Exception: pass
        finally:
            with self.lock:
                if generation == self.generation: self._finish('ended')

    def clear(self):
        with self.lock:
            if self.state in ACTIVE: raise ValueError('Bitte zuerst das Gespräch beenden.')
            self.history = []; self.areas = []; self.error = ''; self.state = 'idle'
            return self.public()

    def _finish(self, state, error=''):
        self.device_tools = False
        self.device_key = None
        if self.native:
            try: self.native.close()
            except Exception: pass
            self.native = None
        self.state, self.error = state, error
        self.lease = self.answer = None
        self.generation += 1
        self._persist_history()
        self.finished.set()

    def _persist_history(self):
        # Checkpoint at most every 15s while speaking; flush all turns on finish.
        try:
            if self.history:
                filename = self.root / ('conversation-' + str(int(self.started_at * 1000)) + '.json')
                atomic_write(filename, json.dumps({'binding': self.binding, 'areas': self.areas,
                    'started_at': self.started_at, 'state': self.state, 'history': self.history}, ensure_ascii=False))
                os.chmod(filename, 0o600)
            self.history_dirty = False
        except OSError:
            self.error = 'Der Gesprächsverlauf konnte nicht dauerhaft gespeichert werden.'

    def display_snapshot(self, binding):
        with self.lock:
            if self.binding != binding or self.cdb.generation != getattr(self, 'account_generation', None):
                return {'session': '', 'state': 'idle', 'areas': [], 'history': []}
            return {'session': str(getattr(self, 'started_at', '')) if self.history or self.state in ACTIVE else '',
                    'state': self.state, 'areas': [a.get('label') or a.get('name', '') for a in self.areas],
                    'history': [{'role': h['role'], 'text': h['text']} for h in self.history]}

    def _frame(self, generation, event, data):
        with self.lock:
            if generation != self.generation or self.state not in ACTIVE: return
            if event == 'state' and self.state != 'closing' and data.get('state') in ('connecting', 'listening', 'thinking', 'speaking'):
                self.state = data['state']
            elif event == 'transcript' and data.get('role') in ('user', 'assistant') and isinstance(data.get('delta'), str):
                self._transcript(data)
                if data.get('role')=='user' and self.native and hasattr(self.native,'note_user_speech'):
                    self.native.note_user_speech()
            elif event == 'search' and self.state!='closing':
                self.searches.update('brain',data.get('call_id'),data.get('status'))
                if self.native and hasattr(self.native,'update_search'):
                    self.native.update_search('brain',data.get('call_id'),data.get('status'))
            elif event == 'closed': self._finish('ended')

    def _transcript(self, data):
        if self.owner_kind == "device": self.deadline = self.clock()+120
        self._append_transcript(data)

    def _append_transcript(self, data):
        """Join each speaker's concurrent stream independently.

        TQS currently supplies no utterance ID: start/end are audio offsets, not
        turn boundaries. A >2s gap gives a new visual turn; without offsets the
        same rule uses arrival time. Changing speaker alone is never a boundary:
        a delayed final syllable can arrive after the assistant already began.
        """
        role, delta = data['role'], data['delta']
        if not delta: return
        def ms(value):
            return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None
        start, end = ms(data.get('start_ms')), ms(data.get('end_ms'))
        identifier = data.get('item_id') or data.get('turn_id')
        if not isinstance(identifier, str): identifier = None
        if start is not None or end is not None or identifier:
            key = (role, identifier, start, end, delta)
            if key in self.seen_transcripts: return
            self.seen_transcripts.add(key)
        previous = self.transcript_turns.get(role)
        timestamp = self.clock()
        same_turn = previous is not None
        if previous:
            if identifier is not None: same_turn = identifier == previous['identifier']
            elif start is not None and previous['offset'] is not None:
                same_turn = start - previous['offset'] <= 2000
            else: same_turn = timestamp - previous['received'] <= 2
        if not same_turn:
            row = {'role': role, 'text': delta.lstrip()}
            self.history.append(row)
            previous = {'row': row, 'identifier': identifier, 'offset': None, 'received': timestamp}
            self.transcript_turns[role] = previous
        else: previous['row']['text'] += delta
        previous['received'] = timestamp
        if end is not None or start is not None:
            previous['offset'] = max(previous['offset'] or 0, end if end is not None else start)
        self.history_dirty = True

    def _read_events(self, handle, binding, callback):
        session = self.cdb.session(binding)
        request = urllib.request.Request(session['server'] + BASE + '/sessions/' + handle + '/events',
            headers={'Authorization': 'Bearer ' + session['token'], 'Accept': 'text/event-stream', 'User-Agent': USER_AGENT})
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args): return None
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(), HTTPSHandler())
        with opener.open(request, timeout=35) as response:
            event = ''; lines = []; size = 0
            for raw in response:
                if self.stop.is_set() or not self.busy(): return
                size += len(raw)
                if size > 1_000_000: raise ValueError('Live event too large')
                line = raw.decode('utf-8').rstrip('\r\n')
                if not line:
                    if lines:
                        value = json.loads('\n'.join(lines))
                        if isinstance(value, dict): callback(event, value)
                    event = ''; lines = []; size = 0
                elif line.startswith('event:'): event = line[6:].strip()
                elif line.startswith('data:'): lines.append(line[5:].lstrip())

    def _events(self, generation, handle, binding):
        failures = 0
        while failures < 9:
            with self.lock:
                if generation != self.generation or self.state == 'closing': return
            opened = self.clock()
            framed = [False]
            def receive(name, data):
                if name != 'error': framed[0] = True
                self._frame(generation, name, data)
            try: self.event_reader(handle, binding, receive)
            except Exception: pass
            with self.lock:
                if generation != self.generation or self.state == 'closing': return
                self.state = 'reconnecting'
            # A healthy server stream may have a time limit. Only consecutive unhealthy
            # reopenings consume the retry budget (same lifecycle rule as mobile).
            failures = 1 if framed[0] or self.clock() - opened >= 30 else failures + 1
            if self.stop.wait(min(8, .5 * 2 ** (failures - 1))): return
        self.end()
        with self.lock: self.error = 'Verbindung zum Gespräch unterbrochen. Bitte erneut starten.'

    def _voice_end_requested(self):
        # TQS sends incremental user transcripts, not a final-utterance event.
        # Wait for a quiet interval so a continuation/negation can cancel the
        # candidate. Never scan assistant speech, sources or arbitrary substrings.
        turn = self.transcript_turns.get('user')
        if not turn or self.muted or self.state in ('connecting', 'closing', 'reconnecting'): return False
        if self.cdb.generation != getattr(self, 'account_generation', None): return False
        if not 1.5 <= self.clock() - turn['received'] <= 6: return False
        text = turn['row']['text'].strip().casefold()
        if '?' in text or any(c in text for c in ('"', '„', '“', '«', '»')): return False
        text = re.sub(r'[.,!;:]', ' ', text)
        return END_COMMAND.fullmatch(' '.join(text.split())) is not None

    def _watch(self):
        while not self.stop.wait(1):
            with self.lock:
                if self.state not in ACTIVE or self.state == 'closing': continue
                if self._voice_end_requested():
                    self.end_reason = 'voice_command'
                    self.end()
                    continue
                if getattr(self, 'history_dirty', False) and self.clock()-getattr(self, 'last_checkpoint', 0) >= 15:
                    self._persist_history(); self.last_checkpoint = self.clock()
                expired = self.clock() > min(self.deadline, self.maximum) or self.cdb.generation != getattr(self, 'account_generation', None)
                handle, binding = self.handle, self.binding
                heartbeat = handle and self.clock() - self.last_heartbeat >= self.heartbeat_seconds
                if heartbeat: self.last_heartbeat = self.clock()
            if expired: self.end(); continue
            if heartbeat:
                try: self.cdb.call(BASE + '/sessions/' + handle + '/heartbeat', {}, binding=binding)
                except Exception: self.end()

    def _device_loop(self, generation, handle, binding):
        while not self.stop.wait(1):
            with self.lock:
                if generation!=self.generation or self.handle!=handle or self.state not in ACTIVE or self.state=='closing': return
            try: self._device_commands(handle,binding)
            except Exception: pass  # Retry receipt; never block voice heartbeat or microphone release.

    def _device_commands(self, handle, binding):
        with self.lock:
            key = self.device_key
            generation = self.generation
            if not key or self.state not in ACTIVE or self.state=='closing': return
        path=BASE+'/sessions/'+handle+'/device-tools'
        response=self.cdb.call(path,{'key':key},binding=binding)
        requests=response.get('requests',[])
        if not isinstance(requests,list) or len(requests)>64: raise ValueError('Ungültige Geräteaufträge.')
        for request in requests:
            with self.lock:
                if generation!=self.generation or handle!=self.handle or self.state not in ACTIVE or self.state=='closing' or self.cdb.generation!=self.account_generation:
                    return
                # The generation check and SQLite commit are indivisible to end/logout.
                result=self.device_executor({'binding':binding,'handle':handle},request)
            self.cdb.call(path,{'key':key,'id':request['id'],'result':result},binding=binding)

    def close(self):
        self.end()
        self.finished.wait(3)
        self.stop.set()
