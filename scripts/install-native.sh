#!/usr/bin/env bash
# Explicit native runtime setup; does not touch existing meetings or old venv.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"
if [[ $(uname -s) != Linux || $(uname -m) != aarch64 ]]; then
  echo 'Dieses Skript ist für Debian/Raspberry Pi OS arm64.' >&2; exit 1
fi
sudo -n apt-get update
sudo -n apt-get install -y python3-venv libportaudio2 libsndfile1 alsa-utils ffmpeg espeak-ng wvkbd cmake build-essential curl zstd
(cd vendor && sha256sum -c SHA256SUMS)
python3 -m venv venv-local-ai
venv-local-ai/bin/pip install -r requirements.txt
printf '%s\n' 'Native Umgebung bereit. Whisper/Ollama-Runtime gemäß docs/LOCAL_AI.md installieren.' 'Keine Modelle wurden heruntergeladen. Bestehende venv bleibt unverändert.'
