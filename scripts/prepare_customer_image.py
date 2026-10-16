#!/usr/bin/env python3
"""Export a clean, allowlisted pi-gen build kit. Never reads a Pi or disk image."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

SOURCE = Path(__file__).resolve().parents[1]
PIN = 'd346cd53562b3c6b4f94c9155175f814258c456d'
sys.path.insert(0, str(SOURCE))
from fleet.releases import allowed


def prepare(output, public_key, server='https://cdblab.de/devices', country='DE'):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    key = Path(public_key).read_bytes()
    if not isinstance(load_pem_public_key(key), Ed25519PublicKey): raise ValueError('Public Ed25519 key required')
    url = urlsplit(server)
    if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment or any(c in server for c in '\n\r'):
        raise ValueError('HTTPS management URL required')
    if not re.fullmatch('[A-Z]{2}', country): raise ValueError('Two-letter WLAN country required')
    output = Path(output).resolve()
    if output.exists(): raise ValueError('Use a NEW output directory; never overlay an installation')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=SOURCE).strip():
        raise ValueError('Commit tracked changes before exporting an image; source_commit must match its inputs')
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=SOURCE).decode().split('\0')
    source = output / 'stage-brain/00-brain/files/source'
    factory = output / 'stage-brain/00-brain/files/factory'
    source.mkdir(parents=True); factory.mkdir()
    files = {}
    for name in filter(None, names):
        selected = allowed(name) or name.startswith('fleet/') and name.endswith('.py') or name in ('requirements.txt','requirements-engine.txt','requirements-wake.txt','vendor/raspberry_pi_meeting_recorder-0.2.7-py3-none-any.whl')
        if not selected: continue
        src = SOURCE / name
        if src.is_symlink(): raise ValueError('No source symlinks allowed')
        target = source / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, target)
        files[name] = hashlib.sha256(src.read_bytes()).hexdigest()
    version = re.search(r"VERSION = '([^']+)'", (source / 'web_server.py').read_text())[1]
    for src in (SOURCE / 'deploy/customer-image').iterdir():
        if src.suffix in ('.py','.service') or src.name == 'install-runtimes.sh':
            shutil.copyfile(src, factory / src.name)
    rule = SOURCE / 'config/udev/70-cdb-respeaker.rules'
    if rule.exists(): shutil.copyfile(rule, factory / rule.name)
    shutil.copyfile(SOURCE / 'scripts/audit_customer_rootfs.py', factory / 'audit_customer_rootfs.py')
    shutil.copyfile(SOURCE / 'kiosk.sh', factory / 'kiosk.sh'); (factory / 'kiosk.sh').chmod(0o755)
    (factory / 'release-public.pem').write_bytes(key)
    metadata = {'version': version, 'server': server, 'country': country, 'pi_gen_commit': PIN,
                'source_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE).decode().strip(),
                'source_files': files, 'public_key_sha256': hashlib.sha256(key).hexdigest(),
                'status': 'prepared-not-boot-certified'}
    (output / 'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    (factory / 'source-manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    (output / 'stage-brain/00-brain/files/factory.json').write_text(json.dumps({'version':version,'server':server,'source_commit':metadata['source_commit'],'pi_gen_commit':PIN}))
    stage = output / 'stage-brain'; step = stage / '00-brain'
    (stage / 'prerun.sh').write_text('#!/bin/bash\nif [ ! -d "${ROOTFS_DIR}" ]; then copy_previous; fi\n')
    (stage / 'EXPORT_IMAGE').write_text("IMG_SUFFIX='-brain'\n")
    (step / '00-packages').write_text('python3-venv libportaudio2 libsndfile1 alsa-utils ffmpeg espeak-ng chromium labwc dbus-user-session pipewire pipewire-pulse wireplumber pulseaudio-utils libspa-0.2-bluetooth network-manager bluez libxcb-cursor0 libegl1 libopengl0 lightdm cmake build-essential curl git zstd\n')
    (step / '00-run.sh').write_text('#!/bin/bash\nset -euo pipefail\ntest -n "${ROOTFS_DIR}" && test "${ROOTFS_DIR}" != /\nmkdir -p "${ROOTFS_DIR}/opt/cdb"\ncp -a files/source files/factory "${ROOTFS_DIR}/opt/cdb/"\ninstall -m 644 files/factory.json "${ROOTFS_DIR}/etc/cdb-factory-image.json"\ntouch "${ROOTFS_DIR}/.cdb-image-build"\n')
    shutil.copyfile(SOURCE / 'deploy/customer-image/01-run-chroot.sh', step / '01-run-chroot.sh')
    (step / '02-run.sh').write_text('#!/bin/bash\nset -euo pipefail\npython3 files/factory/audit_customer_rootfs.py "${ROOTFS_DIR}"\n')
    for script in (stage / 'prerun.sh', step / '00-run.sh', step / '01-run-chroot.sh', step / '02-run.sh'): script.chmod(0o755)
    (output / 'config').write_text("IMG_NAME='cdb-brain-"+version+"'\nRELEASE=trixie\nARCH=arm64\nPI_GEN_RELEASE='CDB Brain customer candidate'\nSTAGE_LIST='stage0 stage1 stage2 stage3 stage-brain'\nFIRST_USER_NAME=cdb\nDISABLE_FIRST_BOOT_USER_RENAME=1\nENABLE_CLOUD_INIT=0\nENABLE_SSH=0\nPASSWORDLESS_SUDO=0\nWPA_COUNTRY="+country+"\nLOCALE_DEFAULT=de_DE.UTF-8\nKEYBOARD_KEYMAP=de\nTIMEZONE_DEFAULT=Europe/Berlin\nDEPLOY_COMPRESSION=xz\n")
    (output / 'build.sh').write_text('''#!/bin/bash
set -euo pipefail
MODE=${1:-native}
if [[ $MODE == --docker ]]; then
  [[ $(docker info --format '{{.Architecture}}') == aarch64 ]] || { echo 'An ARM64 Docker engine is required'; exit 1; }
else
  [[ $MODE == native && $(uname -s) == Linux && $(uname -m) == aarch64 ]] || { echo 'Use --docker on an ARM64 Mac or a dedicated ARM64 Linux builder; never the active Pi.'; exit 1; }
fi
cd -- "$(dirname -- "$0")"
python3 - <<'VERIFY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('manifest.json').read_text())
for name, expected in manifest['build_files'].items():
    path = Path(name)
    if path.is_absolute() or '..' in path.parts or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Build kit integrity check failed: ' + name)
print('Build kit verified; source commit:', manifest['source_commit'])
VERIFY
test ! -e pi-gen || { echo 'Use a fresh build directory'; exit 1; }
git clone https://github.com/RPi-Distro/pi-gen.git pi-gen
git -C pi-gen checkout --detach '''+PIN+'''
# Upstream's Docker builder lacks Python, which our offline rootfs audit needs.
sed -i.bak 's/git vim parted/git vim parted python3/' pi-gen/Dockerfile
cp config pi-gen/config
# Random build-only password is locked before export, never shared with customers.
printf 'FIRST_USER_PASS=%s\\n' "$(openssl rand -hex 32)" >> pi-gen/config
cp -a stage-brain pi-gen/
touch pi-gen/stage2/SKIP_IMAGES
cd pi-gen
if [[ $MODE == --docker ]]; then
  printf 'CONTAINER_NAME=cdb_image_%s\\nPRESERVE_CONTAINER=1\\n' "$(date +%s)" >> config
  ./build-docker.sh
else
  sudo ./build.sh
fi
''')
    (output / 'build.sh').chmod(0o755)
    metadata['build_files'] = {str(path.relative_to(output)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(output.rglob('*')) if path.is_file() and path.name != 'manifest.json'}
    (output / 'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n')
    return metadata

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--public-key',required=True);p.add_argument('--server',default='https://cdblab.de/devices');p.add_argument('--country',default='DE');a=p.parse_args()
    metadata=prepare(a.output,a.public_key,a.server,a.country)
    print(json.dumps({'output':a.output,'version':metadata['version'],'files':len(metadata['source_files']),'status':metadata['status']}))
