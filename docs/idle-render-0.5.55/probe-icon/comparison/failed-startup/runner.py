"""Bounded external process measurement of an isolated, debugger-free Chrome.
No Pi access, audio, cloud calls, product edits or remote debugging connection.
"""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

OUT = Path(os.environ['CDB_COMPARISON_ROOT']) / os.environ['CDB_COMPARISON_MODE'] / 'run'
REPO = OUT.parent
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
UPSTREAM = 'http://127.0.0.1:8099'
DURATION = 1800
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(UPSTREAM + '/api/state', timeout=5) as response:
    preflight = json.load(response)
assert preflight.get('preview') is True, 'Synthetic preview required'
OUT.mkdir(exist_ok=False)
profile = Path(tempfile.mkdtemp(prefix='cdb-unattached-profile-'))
lock = threading.Lock()
counts = {}
errors = []
stop = threading.Event()
wake = {'instance': 'synthetic-unattached', 'enabled': True, 'available': True,
        'word': 'Okay KAI', 'phrase': 'okay-kai', 'state': 'listening',
        'message': 'Bereit', 'detections': 0, 'recognized_for': 0, 'testing': False}


def source_hashes():
    return {name: hashlib.sha256((REPO/'studio'/name).read_bytes()).hexdigest()
            for name in ('app.js', 'touch.js', 'device-status.js', 'microphone.js')}


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def log_message(self, *args):
        pass

    def reply(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        with lock:
            errors.append({'at_epoch': time.time(), 'kind': 'unexpected_post'})
        self.reply(405, b'{"error":"Read-only diagnostic proxy"}', 'application/json')

    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.scheme or parsed.netloc or not parsed.path.startswith('/'):
            self.reply(400, b'Invalid local path', 'text/plain')
            return
        try:
            relative = Path(parsed.path.lstrip('/'))
            candidate = REPO/'studio'/relative
            if '..' in relative.parts:
                raise ValueError('Invalid asset path')
            if parsed.path != '/' and not parsed.path.startswith('/api/') and candidate.is_file():
                body = candidate.read_bytes()
                content_type = mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
            elif parsed.path == '/api/wake/status':
                body, content_type = json.dumps(wake).encode(), 'application/json'
            else:
                with opener.open(UPSTREAM + self.path, timeout=5) as response:
                    body = response.read(4_000_001)
                    content_type = response.headers.get('Content-Type', 'application/octet-stream')
                if len(body) > 4_000_000:
                    raise ValueError('Oversized local response')
                if parsed.path == '/api/state':
                    state = json.loads(body)
                    if state.get('preview') is not True:
                        stop.set()
                        raise ValueError('Preview changed')
                    state['wake'] = wake
                    body = json.dumps(state).encode()
            self.reply(200, body, content_type)
            with lock:
                counts[parsed.path] = counts.get(parsed.path, 0) + 1
        except (OSError, ValueError):
            with lock:
                errors.append({'at_epoch': time.time(), 'kind': 'proxy_request_failed', 'path': parsed.path})
            try:
                self.reply(502, b'{"error":"Local diagnostic upstream unavailable"}', 'application/json')
            except OSError:
                pass


def process_snapshot(browser):
    assert browser.poll() is None, 'Diagnostic Chrome exited'
    processes = {}
    for line in subprocess.check_output(['ps', '-axo', 'pid=,ppid=,rss=,lstart=,comm='], text=True).splitlines():
        fields = line.split(None, 8)
        if len(fields) == 9:
            pid, parent, rss = map(int, fields[:3])
            processes[pid] = {'pid': pid, 'parent': parent, 'rss_kib': rss, 'name': Path(fields[8]).name, 'started_at': ' '.join(fields[3:8])}
    assert browser.pid in processes and processes[browser.pid]['name'] == 'Google Chrome'
    selected = {browser.pid}
    while True:
        before = len(selected)
        selected.update(pid for pid, row in processes.items() if row['parent'] in selected)
        if len(selected) == before:
            break
    rows = [processes[pid] for pid in sorted(selected)]
    with lock:
        request_counts, request_errors = dict(counts), len(errors)
    return {'at_epoch': time.time(), 'root_pid': browser.pid, 'processes': rows,
            'browser_rss_kib': sum(row['rss_kib'] for row in rows),
            'request_counts': request_counts, 'proxy_errors': request_errors}


server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
server.daemon_threads = True
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()
url = 'http://127.0.0.1:' + str(server.server_port) + '/'
arguments = [CHROME, '--headless=new', '--no-first-run', '--no-default-browser-check',
             '--disable-background-networking', '--disable-component-update', '--disable-sync',
             '--mute-audio', '--window-size=1280,720', '--user-data-dir=' + str(profile), url]
assert not any('remote-debugging' in argument for argument in arguments)
initial_hashes = source_hashes()
with open('/Applications/Google Chrome.app/Contents/Info.plist', 'rb') as f:
    chrome_version = plistlib.load(f)['CFBundleShortVersionString']
chrome_log = (OUT/'chrome-private.log').open('w')
browser = None
last_pids = []
completed = False
try:
    browser = subprocess.Popen(arguments, stdout=chrome_log, stderr=subprocess.STDOUT, start_new_session=True)
    ready_deadline = time.monotonic() + 30
    while True:
        assert browser.poll() is None, 'Diagnostic Chrome exited during startup'
        with lock:
            ready = counts.get('/api/state', 0) >= 3 and counts.get('/api/wake/status', 0) >= 3
        if ready:
            break
        assert time.monotonic() < ready_deadline, 'Browser did not begin expected polling'
        time.sleep(.25)
    started, monotonic_start = time.time(), time.monotonic()
    plan = {'scope': 'Concurrent Mac original/guarded icon comparison; immutable exported assets, readonly synthetic preview API, no debugger',
            'comparison_mode': os.environ['CDB_COMPARISON_MODE'],
            'source_commit': {'original':'3de5f94','guarded':'d80f558'}[os.environ['CDB_COMPARISON_MODE']],
            'started_at_epoch': started, 'expected_end_epoch': started + DURATION, 'planned_seconds': DURATION,
            'chrome_version': chrome_version, 'browser_pid': browser.pid, 'url': url,
            'preview_backend_version': preflight['version'], 'frontend_hashes': initial_hashes,
            'flags': arguments[1:-1], 'overall_goal_complete': False,
            'readiness_evidence': 'At least three state and wake-status responses; no visual or acoustic verification',
            'limitations': ['No DOM, JS-heap or visual inspection: deliberately no debugger attached.',
                           'Headless Mac Chrome and synthetic loopback proxy differ from Pi kiosk Chromium.',
                           'Both modes run concurrently and share host resources; not an isolated hardware trial.',
                           'API data is synthetic but not frozen; static assets are pinned and hashed.',
                           'Process RSS may double-count shared pages; no forced GC.']}
    (OUT/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    while True:
        assert not stop.is_set(), 'Synthetic preview guard failed'
        row = process_snapshot(browser)
        row['elapsed_seconds'] = time.monotonic() - monotonic_start
        last_pids = [item['pid'] for item in row['processes']]
        with (OUT/'process-memory.jsonl').open('a') as f:
            f.write(json.dumps(row)+'\n')
        print(json.dumps({'elapsed_seconds': round(row['elapsed_seconds']), 'browser_rss_mib': round(row['browser_rss_kib']/1024, 3),
                          'state_requests': row['request_counts'].get('/api/state'), 'wake_requests': row['request_counts'].get('/api/wake/status'), 'proxy_errors': row['proxy_errors']}), flush=True)
        if row['elapsed_seconds'] >= DURATION:
            break
        time.sleep(min(60, max(0, DURATION - (time.monotonic()-monotonic_start))))
    assert source_hashes() == initial_hashes, 'Frontend changed during observation'
    completed = True
    (OUT/'sampler-complete.json').write_text(json.dumps({'completed': True, 'elapsed_seconds': row['elapsed_seconds'], 'at_epoch': time.time()}, indent=2)+'\n')
finally:
    if browser and browser.poll() is None:
        browser.terminate()
        try:
            browser.wait(timeout=10)
        except subprocess.TimeoutExpired:
            browser.kill()
            browser.wait(timeout=5)
    server.shutdown()
    server.server_close()
    server_thread.join(3)
    chrome_log.close()
    time.sleep(1)
    remaining = subprocess.run(['ps', '-p', ','.join(map(str, last_pids or ([browser.pid] if browser else []))), '-o', 'pid=,comm='], capture_output=True, text=True).stdout.strip() if browser else ''
    cleanup = {'at_epoch': time.time(), 'browser_exit_code': browser.returncode if browser else None,
               'closed': not remaining, 'remaining_processes': remaining, 'completed_observation': completed,
               'proxy_thread_stopped': not server_thread.is_alive(), 'overall_goal_complete': False}
    (OUT/'cleanup.json').write_text(json.dumps(cleanup, indent=2)+'\n')
    (OUT/'proxy-counters.json').write_text(json.dumps({'counts': counts, 'errors': errors}, indent=2)+'\n')
    if not remaining:
        shutil.rmtree(profile)
