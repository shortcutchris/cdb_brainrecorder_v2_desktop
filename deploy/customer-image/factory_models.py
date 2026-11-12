"""Seed a clean factory root with the two models recommended by Recorder Studio."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

WHISPER = 'ggml-medium.bin'
WHISPER_SHA = '6c14d5adee5f86394037b4e4e8b59f1673b6cee10e3cf0b11bbdbee79c156208'
WHISPER_URL = 'https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/'
REGISTRY = 'https://registry.ollama.ai/v2/library/qwen3'
MANIFEST_SHA = '0edcdef34593eac1aa2be9c7d06c432dcf81945adca5eca2f27662c18f168ba0'
LICENSE_URL = 'https://raw.githubusercontent.com/openai/whisper/86098128c0b4f24f0e2aa2994de830614b474227/LICENSE'
LICENSE_SHA = 'b5d65a59060e68c4ff940e1eddfa6f94b2d68fdf58ed7f4dd57721c997e35e9d'


def verify(path, digest):
    with path.open('rb') as stream:
        checksum = hashlib.sha256()
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            checksum.update(chunk)
        actual = checksum.hexdigest()
    if actual != digest:
        raise ValueError('Model bundle checksum mismatch: ' + path.name)


def asset(url, path, digest, download):
    if download and not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent) as tmp:
            subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                            '--proto', '=https', '--proto-redir', '=https', '--retry', '3',
                            '--output', tmp.name, url], check=True)
            verify(Path(tmp.name), digest)
            os.chmod(tmp.name, 0o644)
            os.link(tmp.name, path)
    else:
        verify(path, digest)


def bundle(root, download=False):
    models = root / 'var/lib/ollama/models'
    licenses = root / 'usr/share/doc/cdb-models'
    asset(WHISPER_URL + WHISPER, root / 'opt/cdb/models' / WHISPER, WHISPER_SHA, download)
    asset(LICENSE_URL, licenses / 'Whisper-LICENSE', LICENSE_SHA, download)
    manifest = models / 'manifests/registry.ollama.ai/library/qwen3/4b-instruct'
    asset(REGISTRY + '/manifests/4b-instruct', manifest, MANIFEST_SHA, download)
    data = json.loads(manifest.read_bytes())
    for layer in [data['config'], *data['layers']]:
        digest = layer['digest'].removeprefix('sha256:')
        blob = models / 'blobs' / ('sha256-' + digest)
        asset(REGISTRY + '/blobs/' + layer['digest'], blob, digest, download)
        if blob.stat().st_size != layer['size']:
            raise ValueError('Incomplete Ollama layer')
        if layer['mediaType'] == 'application/vnd.ollama.image.license':
            if download:
                shutil.copyfile(blob, licenses / 'Qwen-LICENSE')
            verify(licenses / 'Qwen-LICENSE', digest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if args.download and not (args.root / '.cdb-image-build').is_file():
        parser.error('Only download inside a fresh image build')
    bundle(args.root, args.download)
