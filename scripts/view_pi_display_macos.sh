#!/bin/bash
# Open the physical Wayland display. Pass the same SSH options and host as for maintenance.
set -eu
if [[ $# -eq 0 || "$(uname -s)" != Darwin ]]; then
    echo 'Auf dem Mac starten: view_pi_display_macos.sh [SSH-Optionen] benutzer@pi' >&2
    exit 2
fi
port=${CDB_DISPLAY_PORT:-15971}
if ! [[ "$port" =~ ^[0-9]+$ ]] || (( port < 1024 || port > 65535 )); then
    echo 'Ungültiger lokaler Port.' >&2
    exit 2
fi
viewer_app=/Applications/TigerVNC.app
if [[ ! -d "$viewer_app" ]]; then
    echo 'Bitte TigerVNC Viewer auf dem Mac installieren (brew install --cask tigervnc).' >&2
    exit 1
fi
if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null; then
    echo "Port $port ist belegt. Ist das Pi-Display bereits geöffnet?" >&2
    exit 1
fi
session=$(mktemp -d)
cleanup() {
    if [[ -n "${tunnel_pid:-}" ]]; then
        kill "$tunnel_pid" 2>/dev/null || true
        wait "$tunnel_pid" 2>/dev/null || true
    fi
    rm -rf "$session"
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP

# A private socket on the Pi avoids exposing any VNC listener on its network.
# Stream-local forwarding requires knowing the absolute remote socket path.
ssh_opts=(-T -o BatchMode=yes -o StrictHostKeyChecking=yes -o ForwardAgent=no -o ConnectTimeout=8)
remote_dir=$(ssh "${ssh_opts[@]}" "$@" 'umask 077; mktemp -d "${XDG_RUNTIME_DIR:?}/studio-display.XXXXXXXX"')
if ! [[ "$remote_dir" =~ ^/run/user/[0-9]+/studio-display\.[[:alnum:]]+$ ]]; then
    echo 'Kein privates Verzeichnis für den Bildschirmzugriff verfügbar.' >&2
    exit 1
fi
ssh "${ssh_opts[@]}" -o ExitOnForwardFailure=yes -o ServerAliveInterval=15 -o ServerAliveCountMax=2 \
    -L "127.0.0.1:$port:$remote_dir/display" "$@" "sh -s -- '$remote_dir'" >"$session/status" <<'REMOTE' &
set -eu
dir=$1
cleanup() {
    if [ -n "${viewer:-}" ]; then
        kill "$viewer" 2>/dev/null || true
        wait "$viewer" 2>/dev/null || true
    fi
    rm -rf "$dir"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
export WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-wayland-0}
wayvnc -C /dev/null -R -e -f 10 -k de -n 'Recorder Studio am Pi' \
    -S "$dir/control" -u "$dir/display" &
viewer=$!
while [ ! -S "$dir/display" ]; do
    kill -0 "$viewer"
    sleep .1
done
echo ready
wait "$viewer"
REMOTE
tunnel_pid=$!
for (( i=0; i<150; i++ )); do
    if grep -qx ready "$session/status"; then
        open -na "$viewer_app" --args -SecurityTypes None -AcceptClipboard=0 -SendClipboard=0 "127.0.0.1::$port"
        wait "$tunnel_pid"
        exit 0
    fi
    kill -0 "$tunnel_pid" 2>/dev/null || { wait "$tunnel_pid"; exit 1; }
    sleep .1
done
echo 'Pi-Bildschirm wurde nicht rechtzeitig bereit.' >&2
exit 1
