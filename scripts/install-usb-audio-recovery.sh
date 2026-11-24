#!/bin/bash
# Explicit system setup; never run by an ordinary signed app update.
set -euo pipefail
[[ $(id -u) == 0 ]] || { echo 'Bitte als Administrator ausführen.' >&2; exit 1; }
[[ $# == 1 && $1 =~ ^[a-z_][a-z0-9_-]{0,31}$ ]] || { echo 'Genau einen bestehenden Gerätebenutzer angeben.' >&2; exit 1; }
[[ $(uname -s) == Linux ]] || { echo 'Nur für den Raspberry-Pi-Linux-Host.' >&2; exit 1; }
target_user=$1
getent passwd "$target_user" >/dev/null || { echo 'Gerätebenutzer fehlt.' >&2; exit 1; }
[[ $(id -u "$target_user") != 0 ]] || { echo 'Ein unprivilegierter Gerätebenutzer ist erforderlich.' >&2; exit 1; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
helper_source="$source_dir/deploy/usb-audio-recovery/cdb-usb-audio-recover.py"
[[ -f $helper_source && ! -L $helper_source ]] || { echo 'Helferquelle fehlt.' >&2; exit 1; }
for path in /usr /usr/local /etc /etc/sudoers.d; do
    [[ -d $path && ! -L $path && $(stat -c %u "$path") == 0 ]] || { echo 'Unsicherer Installationspfad.' >&2; exit 1; }
    [[ $(( 8#$(stat -c %a "$path") & 8#022 )) == 0 ]] || { echo 'Beschreibbarer Installationspfad.' >&2; exit 1; }
done
if [[ ! -e /usr/local/sbin ]]; then install -d -o root -g root -m 0755 /usr/local/sbin; fi
[[ -d /usr/local/sbin && ! -L /usr/local/sbin && $(stat -c %u /usr/local/sbin) == 0 ]] || exit 1
[[ $(( 8#$(stat -c %a /usr/local/sbin) & 8#022 )) == 0 ]] || exit 1
helper_tmp=$(mktemp /usr/local/sbin/.cdb-usb-audio.XXXXXX)
sudoers_tmp=$(mktemp /etc/sudoers.d/.cdb-usb-audio.XXXXXX)
trap 'rm -f -- "$helper_tmp" "$sudoers_tmp"' EXIT
install -o root -g root -m 0755 "$helper_source" "$helper_tmp"
/usr/bin/python3 -I -c 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read())' "$helper_tmp"
printf '%s ALL=(root) NOPASSWD: NOSETENV: /usr/local/sbin/cdb-usb-audio-recover check, /usr/local/sbin/cdb-usb-audio-recover recover\n' "$target_user" > "$sudoers_tmp"
chown root:root "$sudoers_tmp"
chmod 0440 "$sudoers_tmp"
visudo -cf "$sudoers_tmp"
mv -f -- "$helper_tmp" /usr/local/sbin/cdb-usb-audio-recover
mv -f -- "$sudoers_tmp" /etc/sudoers.d/cdb-usb-audio-recovery
echo 'USB-Audio-Helfer eingerichtet. Keine Geräte neu gestartet oder Einstellungen geändert.'
