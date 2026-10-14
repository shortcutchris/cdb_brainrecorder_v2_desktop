"""Signed, code-only releases. Runtime/dependency and schema changes fail closed.

The independent agent never executes a release-supplied installer. An fsynced
journal makes interrupted activation roll back before another command is accepted.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import time
import zipfile
from .common import read, save

MAX_BYTES=32*1024*1024
ROOT_FILES={'web_server.py','settings.py','config.py'}
ROOT_DIRS={'studio','services','data','utils','prompts'}


def allowed(name):
    p=PurePosixPath(name)
    return (not p.is_absolute() and '..' not in p.parts and '\\' not in name and
            (name in ROOT_FILES or name in ('fleet/__init__.py','fleet/common.py') or (len(p.parts)>1 and p.parts[0] in ROOT_DIRS and (p.suffix in ('.py','.js','.css','.html','.svg','.wav','.json','.png','.ico','.md') and 'sessions' not in p.name))) and
            not any(part.startswith('.') or part=='__pycache__' for part in p.parts))


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def verify(bundle,key,architecture,runtime,previous,sequence):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    public=load_pem_public_key(Path(key).read_bytes())
    if not isinstance(public,Ed25519PublicKey):raise ValueError('Ed25519-Schlüssel erforderlich.')
    manifest=bundle['manifest'];public.verify(base64.b64decode(bundle['signature'],validate=True),canonical(manifest))
    if (manifest['format']!=1 or manifest['architecture']!=architecture or manifest['runtime']!=runtime or
        previous not in manifest['from_versions'] or type(manifest['sequence']) is not int or manifest['sequence']<=sequence or
        manifest['schema']!='unchanged' or manifest['expires']<time.time()):raise ValueError('Release nicht kompatibel, veraltet oder abgelaufen.')
    payload=base64.b64decode(bundle['archive'],validate=True)
    if len(payload)>MAX_BYTES or hashlib.sha256(payload).hexdigest()!=manifest['sha256']:raise ValueError('Release beschädigt.')
    files={}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        total=0
        for entry in archive.infolist():
            total+=entry.file_size
            if total>MAX_BYTES or not allowed(entry.filename) or entry.filename in files or (entry.external_attr>>16)&0o170000==0o120000:raise ValueError('Ungültiger Release-Inhalt.')
            files[entry.filename]=archive.read(entry)
    if set(files)!=set(manifest['files']) or 'web_server.py' not in files:raise ValueError('Release unvollständig.')
    if any(hashlib.sha256(value).hexdigest()!=manifest['files'][name] for name,value in files.items()):raise ValueError('Dateiprüfung fehlgeschlagen.')
    return manifest,files


class Updater:
    def __init__(self,root,key,runtime,restart,health,architecture=None):
        self.root=Path(root);self.key=key;self.runtime=runtime;self.restart=restart;self.health=health
        self.architecture=architecture or platform.machine()
        self.root.mkdir(parents=True,exist_ok=True)
        self.current=self.root/'current';self.journal=self.root/'transaction.json';self.ledger=self.root/'accepted.json'

    def link(self,target):
        temp=self.root/'next'
        temp.unlink(missing_ok=True);temp.symlink_to(target,target_is_directory=True);os.replace(temp,self.current)
        fd=os.open(self.root,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)

    def recover(self):
        journal=read(self.journal)
        if not journal:return False
        accepted=read(self.ledger,{})
        # Ledger commit is the transaction boundary; don't undo a confirmed release.
        if accepted.get('release')!=journal['release']:
            self.link(journal['previous']);self.restart()
            if not self.health(journal['previous_version']):raise ValueError('Rückkehr benötigt Unterstützung.')
        self.journal.unlink();return True

    def install(self,bundle):
        self.recover()
        accepted=read(self.ledger)
        if not accepted or not self.current.is_symlink():raise ValueError('Update-Basis nicht eingerichtet.')
        manifest,files=verify(bundle,self.key,self.architecture,self.runtime,accepted['version'],accepted['sequence'])
        release=hashlib.sha256(canonical(manifest)).hexdigest()
        if shutil.disk_usage(self.root).free<MAX_BYTES*3:raise ValueError('Zu wenig Speicher für Update und Rückkehr.')
        target=self.root/'releases'/release
        if target.exists():shutil.rmtree(target)
        target.mkdir(parents=True)
        for name,value in files.items():
            path=target/name;path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('wb') as stream:stream.write(value);stream.flush();os.fsync(stream.fileno())
        # Dependencies and models stay outside version directories. No executable hooks.
        shared=read(self.root/'shared.json',{})
        for name in ('models',):
            if shared.get(name):(target/name).symlink_to(shared[name],target_is_directory=True)
        previous=str(self.current.resolve())
        save(self.journal,{'previous':previous,'previous_version':accepted['version'],'release':release})
        try:
            self.link(target);self.restart()
            if not self.health(manifest['version']):raise ValueError('Startprüfung fehlgeschlagen.')
            save(self.ledger,{'version':manifest['version'],'sequence':manifest['sequence'],'release':release})
            self.journal.unlink()
            return 'updated'
        except Exception:
            self.recover()
            raise ValueError('Update fehlgeschlagen; vorherige Version wiederhergestellt.') from None


def package(source,key,version,previous,sequence,runtime,expires):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    source=Path(source)
    if subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=source).strip():
        raise ValueError('Nur einen sauberen, committed Stand signieren.')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source).decode().strip()
    names=subprocess.check_output(['git','ls-files','-z'],cwd=source).decode().split('\0')
    files={name:(source/name).read_bytes() for name in names if name and allowed(name)}
    archive=io.BytesIO()
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as out:
        for name,value in files.items():out.writestr(name,value)
    payload=archive.getvalue()
    manifest={'format':1,'commit':commit,'version':version,'from_versions':previous,'sequence':sequence,'architecture':'aarch64','runtime':runtime,'schema':'unchanged','expires':expires,'sha256':hashlib.sha256(payload).hexdigest(),'files':{k:hashlib.sha256(v).hexdigest() for k,v in files.items()}}
    signature=load_pem_private_key(Path(key).read_bytes(),None).sign(canonical(manifest))
    return {'manifest':manifest,'signature':base64.b64encode(signature).decode(),'archive':base64.b64encode(payload).decode()}
