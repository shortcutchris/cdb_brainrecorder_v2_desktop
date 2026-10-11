#!/usr/bin/env bash
# Install application launchers only; no packages, models or firmware changes.
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
test -x "$root/venv-local-ai/bin/python"
test -x /usr/bin/chromium
mkdir -p "$HOME/.config/systemd/user" "$HOME/.config/autostart" "$HOME/Desktop"
cat > "$HOME/.config/systemd/user/cdb-recorder-studio.service" <<EOF
[Unit]
Description=Corporate Digital Brain Recorder Python Studio
After=network.target

[Service]
Type=simple
WorkingDirectory=$root
ExecStart=$root/venv-local-ai/bin/python $root/web_server.py --port 8088 --database $root/data/sessions.db
Environment=PYTHONUNBUFFERED=1
Environment=LANG=C.UTF-8
Environment=LC_ALL=C.UTF-8
Environment=PYTHONIOENCODING=utf-8
Environment=XDG_RUNTIME_DIR=/run/user/$(id -u)
Environment=WAYLAND_DISPLAY=wayland-0
UMask=0077
Restart=on-failure
RestartSec=3
TimeoutStopSec=45
KillMode=control-group

[Install]
WantedBy=default.target
EOF
cat > "$HOME/.config/autostart/cdb-recorder.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Corporate Digital Brain Recorder
Comment=Lokales Recorder Studio mit Python-Backend
Exec=$root/kiosk.sh
Path=$root
Icon=$root/icon.png
Terminal=false
Categories=AudioVideo;Audio;Recorder;
StartupNotify=true
X-GNOME-Autostart-enabled=true
EOF
cp "$HOME/.config/autostart/cdb-recorder.desktop" "$HOME/Desktop/cdb-recorder.desktop"
chmod +x "$HOME/Desktop/cdb-recorder.desktop" "$root/kiosk.sh"
systemctl --user daemon-reload
systemctl --user enable --now cdb-recorder-studio.service
