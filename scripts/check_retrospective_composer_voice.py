"""Opt-in Staging acceptance on a Pi: synthetic speech -> workflow -> Composer.

Uses the installed app in isolated storage, never the room microphone/speaker.
Creates one test board only on spoken request. Credentials are copied privately
on the Pi and removed in finally. Does not install, restart or alter the kiosk.
Run with the Pi's app Python; see docs/workflow-catalog/retrospective-composer.md.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo


INPUTS = [
    ('goal', 'Wir blicken auf den Teamworkshop am Montag im Testprojekt Alpha zurück. Unser Ziel ist eine bessere Vorbereitung. Halte das als Ziel und Zeitraum fest.', ['alpha', 'teamworkshop', 'montag', 'vorbereitung']),
    ('strengths', 'Gut lief: Die Agenda war klar und alle kamen zu Wort. Halte beide Punkte unter Was lief gut fest.', ['agenda', 'wort']),
    ('challenges', 'Schwierig war: Die Technikprüfung fehlte und die Pause begann zu spät. Halte beide Punkte unter Was war schwierig fest.', ['technik', 'pause']),
    ('learnings', 'Unsere Erkenntnisse sind: Wir müssen die Technik vorher prüfen und Puffer für Pausen einplanen. Halte beides unter Was lernen wir fest.', ['technik', 'puffer', 'pause']),
    ('actions', 'Wir vereinbaren verbindlich: Anna prüft die Technik bis Donnerstag. Ben verschickt die Agenda bis Freitag. Halte beide vereinbarten Verbesserungen mit Namen und Termin fest.', ['anna', 'technik', 'donnerstag', 'ben', 'agenda', 'freitag']),
]


def contains_facts(text, terms):
    # Ignore punctuation/spacing, never substitute a different proper noun.
    normalized = ''.join(c for c in text.casefold() if c.isalnum())
    return all(''.join(c for c in t.casefold() if c.isalnum()) in normalized for t in terms)


def verify_readback(data, titles, sections):
    """Composer read_board returns data.text, a line-based MCP board view.

    Require one correctly titled card per section, exact text apart from
    whitespace, five distinct cards, and membership in the single result frame.
    Extra/missing/truncated/wrongly grouped cards must not pass this check.
    """
    text = data.get('text')
    if not isinstance(text, str): raise AssertionError('Expected Composer data.text')
    frames_text, nodes_text = text.split('\nFrames:\n', 1)[1].split('\nNodes:\n', 1)
    frames = re.findall(r'^- \[([^\]]+)\] ', frames_text, re.MULTILINE)
    assert len(frames) == 1, 'Expected exactly one result frame'
    lines = [s for s in nodes_text.splitlines() if s.startswith('- [')]
    assert len(lines) == len(titles), 'Unexpected card count'
    rows = []
    for line in lines:
        match = re.fullmatch(r'- \[([^\]]+)\] text(?: \([^)]+\))* at \([^)]+\) size \S+ in frame ([^\s:]+): (.*)', line)
        assert match is not None, 'Unexpected or truncated card representation'
        node, frame, content = match.groups()
        assert frame == frames[0], 'Card belongs to the wrong frame'
        rows.append((node, content))
    assert len({node for node, _ in rows}) == len(titles), 'Duplicate card IDs'
    assert len(set(titles.values())) == len(titles)
    result = {}
    for section, title in titles.items():
        matches = [(node, body[len(title)+1:]) for node, body in rows if body.startswith(title+' ')]
        assert len(matches) == 1, 'Missing/duplicate title: '+title
        node, body = matches[0]
        expected = ' '.join(sections[section].split())
        actual = ' '.join(body.split())
        assert actual == expected, 'Text differs in '+section
        result[section] = {'title': title, 'node_id': node, 'frame_id': frames[0],
                           'text': actual, 'text_matches_ignoring_whitespace': True}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--app-source', type=Path, required=True)
    p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--execute-staging-write', action='store_true')
    p.add_argument('--resume-from', type=Path, help='Read back and query the saved board of an earlier run; never republish')
    args = p.parse_args()
    if not args.execute_staging_write: p.error('Explicit --execute-staging-write is required; this creates a test board.')
    source = args.app_source.resolve()
    root = args.output.resolve()
    if root.exists(): p.error('Use a new output directory; existing tests are retained.')
    production = json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/state', timeout=10))
    assert production['room']['signed_in'], 'Sign in at the Pi first'
    assert production['cdb']['config']['server'] == 'https://staging.cdbos.de'
    assert not production['recording']['id'] and not production['live']['busy'] and not production['management']['maintenance']
    assert subprocess.check_output(['timedatectl', 'show', '-p', 'NTPSynchronized', '--value'], text=True).strip() == 'yes'
    root.mkdir(mode=0o700, parents=True)
    sys.path.insert(0, str(source))
    from web_server import StudioApp, VERSION
    from services.live_audio import NativeLiveAudio
    from services.live_conversation import BASE
    from services.workflow_catalog import labels

    class NoProcessing:
        def transcribe(self, *a, **k): raise AssertionError('Recording is not part of this test')
        def generate(self, *a, **k): raise AssertionError('Recording is not part of this test')

    def no_capture(_): raise AssertionError('No room capture allowed')

    app = StudioApp(root/'queue', root/'sessions.db', backend=NoProcessing(),
                    command_factory=no_capture, preview=True, settings_file=root/'settings.ini')
    app.ambient_stop.set(); app.ambient_thread.join(3); app.clock_ready = True
    app.engine.configure({'setup_complete': True})
    report = {'tested_at': datetime.now(ZoneInfo('Europe/Berlin')).isoformat(), 'version': VERSION,
              'source_directory': source.name, 'server': 'https://staging.cdbos.de',
              'synthetic_audio': True, 'room_microphone_used': False, 'room_speaker_used': False,
              'commands': [], 'spoken_inputs': [], 'replies': [], 'composer_calls': []}
    started = time.monotonic(); cursor = 0; last_tool_reply = []; board_response = None
    capture = root/'capture.py'
    capture.write_text("""import sys,time
from pathlib import Path
root=Path(sys.argv[1]);index=1;audio=b''
while True:
 if not audio and (root/f'play-{index}.pcm').exists():
  audio=(root/f'play-{index}.pcm').read_bytes();index+=1
 chunk,audio=audio[:640],audio[640:]
 sys.stdout.buffer.write(chunk.ljust(640,b'\\0'));sys.stdout.buffer.flush();time.sleep(.02)
""")
    config = {'device': 'synthetic', 'speaker': 'synthetic',
              'microphone_label': 'Synthetic acceptance', 'speaker_label': 'Discarded test output'}
    app.live_audio_config = lambda: config; app.live.audio_config = lambda: config
    app.live.audio_factory = lambda conf, failed: NativeLiveAudio(conf, failed,
        capture_command=[sys.executable, str(capture), str(root)],
        playback_command=[sys.executable, '-c', 'import sys\nwhile sys.stdin.buffer.read(960):pass'])
    executor = app.live.device_executor
    cdb_call = app.cdb.call

    def execute(scope, request):
        nonlocal last_tool_reply
        last_tool_reply = [r['text'] for r in app.live.public()['history'] if r['role'] == 'assistant']
        answer = executor(scope, request)
        item = {'name': request['name'], 'ok': answer.get('ok'), 'code': answer.get('code')}
        if 'section' in request['arguments']: item['section'] = request['arguments']['section']
        if 'answer' in request['arguments']: item['answer'] = request['arguments']['answer']
        if 'format' in request['arguments']: item['format'] = request['arguments']['format']
        if 'phase' in request['arguments']: item['phase'] = request['arguments']['phase']
        workshop = answer.get('workshop') or {}
        if workshop.get('composer'): item['composer_state'] = workshop['composer']['state']
        report['commands'].append(item)
        print(json.dumps({'tool': item}, ensure_ascii=False), flush=True)
        return answer

    def call(path, body=None, **kwargs):
        if path == '/api/v1/kb/voice/board-tools/call':
            # Do not log credentials, request IDs or arbitrary remote responses.
            report['composer_calls'].append(body['name'])
        return cdb_call(path, body, **kwargs)

    app.live.device_executor = execute; app.cdb.call = call

    def wait_for(check, timeout=100):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = app.live.public()
            if state['state'] in ('error', 'ended'): raise AssertionError('Live ended: ' + state['error'])
            if check(): return
            time.sleep(.5)
        raise AssertionError('Timed out waiting for the spoken action')

    def speak(text):
        nonlocal cursor
        cursor += 1
        subprocess.run(['espeak-ng', '-v', 'de', '-s', '125', '-w', str(root/'source.wav'), text], check=True)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(root/'source.wav'),
                        '-ar', '16000', '-ac', '1', '-f', 's16le', str(root/'next.pcm')], check=True)
        (root/'next.pcm').replace(root/f'play-{cursor}.pcm')
        report['spoken_inputs'].append(text)
        print(json.dumps({'spoken': text}, ensure_ascii=False), flush=True)

    def settled():
        deadline = time.monotonic()+75; signature = None; stable = time.monotonic()
        while time.monotonic() < deadline:
            state = app.live.public()
            current = [r['text'] for r in state['history'] if r['role'] == 'assistant']
            if current != signature: signature = current; stable = time.monotonic()
            if current != last_tool_reply and time.monotonic()-stable >= 4 and not state['feedback']['output']['active']:
                report['replies'].append(current[-1]); return
            if state['state'] in ('error', 'ended'): raise AssertionError('Live ended: ' + state['error'])
            time.sleep(.5)
        raise AssertionError('Assistant reply did not finish')

    def command(text, name, section=None):
        offset = len(report['commands']); speak(text)
        wait_for(lambda: any(c['name'] == name and c['ok'] and (section is None or c.get('section') == section)
                             for c in report['commands'][offset:]))
        settled()

    try:
        for name in ('session.json', 'config.json', 'destination.json'):
            original = args.data_root/'cdb'/name
            if name == 'destination.json' and not original.exists(): continue
            shutil.copy2(original, app.cdb.root/name); os.chmod(app.cdb.root/name, 0o600)
        assert app.cdb.config()['server'] == report['server']
        app.room.observed_account = app.room.account()
        setup = app.live.setup()
        areas = [a['id'] for a in setup['areas'] if a.get('name') == 'staging_playground' or a.get('label') == 'staging_playground']
        assert areas, 'Only staging_playground may be used'
        app.live.remember_areas(areas[:1], setup['selection_account_key'])
        binding = app.wake_account()
        caps = app.cdb.call(BASE+'/capabilities', binding=binding)
        assert caps.get('workshop_catalog_v1') is True
        ident = None
        if args.resume_from:
            import sqlite3
            previous = json.loads((args.resume_from/'result.json').read_text())
            assert previous['version'] == VERSION and previous['server'] == report['server'] and previous['synthetic_audio']
            assert previous['board']['url'] == 'https://composer-staging.cdbos.de/board/'+str(previous['board']['id'])
            with sqlite3.connect('file:'+str(args.resume_from/'queue/workshops.sqlite3')+'?mode=ro', uri=True) as old_db:
                with sqlite3.connect(root/'queue/workshops.sqlite3') as new_db: old_db.backup(new_db)
            rows = [r for r in app.workshops.list(binding) if r['composer']['board_id'] == previous['board']['id']]
            assert len(rows) == 1
            ident = rows[0]['id']
            report['resumed_existing_board'] = True
            report['original_report_sha256'] = hashlib.sha256((args.resume_from/'result.json').read_bytes()).hexdigest()
            for key in ('expected_sections', 'expected_titles', 'workflow_version', 'spoken_semantic_checks', 'board'):
                report[key] = previous[key]
        lease = app.live.reserve(areas[:1], owner_kind='device', workshop_id=ident)
        app.live.start_native(lease['lease'])
        wait_for(lambda: app.live.public()['state'] == 'listening', 60); time.sleep(4)
        assert app.live.public()['device_tools_version'] == 5
        report['device_tools_version'] = 5

        if args.resume_from:
            expected = report['expected_sections']
            saved = app.workshops.get(binding, ident)
            assert saved['sections'] == expected and saved['composer']['state'] == 'saved'
        else:
            command('Ich möchte jetzt eine Retrospektive starten.', 'request_workshop_mode')
            assert next(c for c in reversed(report['commands']) if c['name'] == 'request_workshop_mode')['format'] == 'retrospective'
            assert 'erklär' in report['replies'][-1].lower() and '?' in report['replies'][-1]
            assert not any(c['name'] == 'answer_workshop_intro' for c in report['commands'])
            report['introduction_waited_for_answer'] = True
            command('Ja, bitte erkläre mir den Ablauf.', 'answer_workshop_intro')
            assert next(c for c in reversed(report['commands']) if c['name'] == 'answer_workshop_intro')['answer'] == 'explain'
            ident = app.live.workshop_id; assert ident
            report['explanation'] = report['replies'][-1]
            for section, spoken, terms in INPUTS:
                command(spoken, 'update_workshop_result', section)
                row = app.workshops.get(binding, ident)
                assert contains_facts(row['sections'][section], terms), 'Missing spoken fact in '+section
            command('Die Retrospektive ist abgeschlossen. Setze die Phase auf Abschließen und lies alle fünf Ergebnisbereiche vor. Bitte noch nichts im Composer speichern.', 'set_workshop_phase')
            row = app.workshops.get(binding, ident)
            assert row['phase'] == 'closing'
            assert not any(c['name'] == 'save_workshop_to_composer' for c in report['commands'])
            assert not report['composer_calls'] and row['composer']['state'] == 'local'
            report['no_unrequested_save'] = True
            expected = dict(row['sections'])
            report['expected_sections'] = expected
            report['expected_titles'] = labels(row['workflow'])
            report['workflow_version'] = row['workflow']['version']
            report['spoken_semantic_checks'] = {section: contains_facts(expected[section], terms) for section, _, terms in INPUTS}
            assert all(report['spoken_semantic_checks'].values())
            command('Speichere diese Retrospektive jetzt als neues Board im Composer.', 'save_workshop_to_composer')
            wait_for(lambda: app.workshops.get(binding, ident)['composer']['state'] != 'saving', 60)
            saved = app.workshops.get(binding, ident)
            assert saved['composer']['state'] == 'saved', saved['composer']['message']
            assert saved['sections'] == expected, 'Results changed during publication'
            report['board'] = {'url': saved['composer']['url'], 'id': saved['composer']['board_id'], 'revision': saved['composer']['revision']}
        board_response = app.cdb.call('/api/v1/kb/voice/board-tools/call',
            {'name': 'read_board', 'args': {'board_id': saved['composer']['board_id']}}, binding=binding)
        assert board_response.get('success') is True
        # Keep the full server envelope private; publish only synthetic field evidence.
        (root/'board-response-private.json').write_text(json.dumps(board_response, ensure_ascii=False, indent=2))
        os.chmod(root/'board-response-private.json', 0o600)
        report['board_response_top_keys'] = sorted(board_response['data'])
        report['readback_fields'] = verify_readback(board_response['data'], report['expected_titles'], expected)
        counts = Counter(report['composer_calls'])
        if args.resume_from:
            assert set(counts) == {'read_board'}
            report['readback_only_no_republication'] = True
        else:
            assert counts['create_board'] == 1 and counts['add_note'] == 5 and counts['add_frame'] == 1
            report['one_board_five_notes_one_frame'] = True
        command('Ist die Retrospektive jetzt erfolgreich im Composer gespeichert? Prüfe bitte den gespeicherten Status.', 'get_workshop')
        assert any(c.get('composer_state') == 'saved' for c in report['commands'])
        report['agent_confirmed_saved'] = True
        report['saved_reply'] = report['replies'][-1]
        assert 'gespeichert' in report['saved_reply'].casefold()
        if args.resume_from:
            assert not any(c['name'] in ('save_workshop_to_composer', 'update_workshop_result', 'set_workshop_phase') for c in report['commands'])
        app.live.end(); app.live.finished.wait(35)
        assert not app.live.busy()
        report['closed_cleanly'] = not app.live.public()['error']
        assert report['closed_cleanly']
        after = json.load(urllib.request.urlopen('http://127.0.0.1:8088/api/state', timeout=10))
        assert after['config'] == production['config'] and after['timers']['items'] == production['timers']['items']
        assert [r['id'] for r in after['sessions']] == [r['id'] for r in production['sessions']]
        report['pi_config_recordings_timers_unchanged'] = True
        report['passed'] = True
    except Exception as error:
        report['passed'] = False
        report['error'] = str(error)
        print(json.dumps({'failed': str(error)}, ensure_ascii=False), flush=True)
    finally:
        app.live.end(); app.live.finished.wait(35)
        report['transcript'] = [{'role': h['role'], 'text': h['text']} for h in app.live.public()['history']]
        app.close()
        for name in ('session.json', 'config.json', 'destination.json'): (app.cdb.root/name).unlink(missing_ok=True)
        report['temporary_credentials_removed'] = not (app.cdb.root/'session.json').exists()
        report['seconds'] = round(time.monotonic()-started, 2)
        report['runner_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (root/'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({'passed': report.get('passed', False), 'result': str(root/'result.json'), 'board': report.get('board')}, ensure_ascii=False), flush=True)
    return 0 if report.get('passed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
