#!/usr/bin/env bash
# One-time optional LED access; no firmware, audio routing or mute changes.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
"$root/venv-local-ai/bin/pip" install 'pyusb==1.3.1'
sudo install -m 0644 "$root/config/udev/70-cdb-respeaker.rules" /etc/udev/rules.d/70-cdb-respeaker.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=usb --attr-match=idVendor=2886 --attr-match=idProduct=001a
sudo udevadm settle
printf '%s\n' 'ReSpeaker-LED-Zugriff eingerichtet. Der Recorder-Benutzer muss Mitglied der Gruppe audio sein.'
