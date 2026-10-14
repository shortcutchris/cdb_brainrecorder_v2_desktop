import hashlib
import json
import os
from pathlib import Path
import tempfile
import urllib.request
from urllib.parse import urlsplit


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def save(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream); stream.flush(); os.fsync(stream.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def read(path, default=None):
    try: return json.loads(Path(path).read_text())
    except FileNotFoundError: return default


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Weiterleitung nicht erlaubt.')


def request(base, path, body=None, token='', limit=1024*1024):
    url = urlsplit(base)
    if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('127.0.0.1', 'localhost')):
        raise ValueError('HTTPS erforderlich.')
    if url.username or url.password or url.query or url.fragment: raise ValueError('Ungültige Serveradresse.')
    headers = {'Content-Type':'application/json'}
    if token: headers['Authorization'] = 'Bearer '+token
    req = urllib.request.Request(base.rstrip('/')+path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
    with urllib.request.build_opener(NoRedirect).open(req, timeout=12) as response:
        raw = response.read(limit+1)
        if len(raw)>limit: raise ValueError('Antwort zu groß.')
        return json.loads(raw)
