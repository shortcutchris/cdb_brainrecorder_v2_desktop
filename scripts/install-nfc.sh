#!/bin/bash
# Optional existing-device migration; does not enable NFC or restart the recorder.
set -euo pipefail
test "$(id -u)" = 0 || { echo 'Bitte mit sudo ausführen.'; exit 1; }
apt-get update
apt-get install -y python3-pyscard pcscd libccid
systemctl enable --now pcscd.socket
/usr/bin/python3 -I -c 'from smartcard.System import readers; print("PC/SC bereit; Leser:", len(readers()))'
