#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
systemctl --user start cdb-recorder-studio.service
for attempt in {1..60}; do
  if curl --silent --fail http://127.0.0.1:8088/api/state >/dev/null; then break; fi
  sleep 1
done
curl --silent --fail http://127.0.0.1:8088/api/state >/dev/null
mkdir -p "$HOME/.local/share/cdb-recorder-kiosk"
exec /usr/bin/flock -n "$HOME/.local/share/cdb-recorder-kiosk/launcher.lock" \
  /usr/bin/chromium --ozone-platform=wayland --kiosk --no-first-run \
  --password-store=basic --disable-background-networking \
  --no-default-browser-check --disable-session-crashed-bubble \
  --user-data-dir="$HOME/.local/share/cdb-recorder-kiosk/browser" \
  http://127.0.0.1:8088/
