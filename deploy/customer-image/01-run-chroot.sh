#!/bin/bash
# Executed by pi-gen in a new rootfs, NEVER an installation script for a live Pi.
set -euo pipefail
test -f /.cdb-image-build || { echo 'Refusing: not a fresh pi-gen image root'; exit 1; }
test "$(dpkg --print-architecture)" = arm64
cd /opt/cdb/source
python3 -m venv /opt/cdb/runtime
/opt/cdb/runtime/bin/pip install --only-binary=:all: -r requirements.txt cryptography==50.0.2 vosk==0.3.45
bash /opt/cdb/factory/install-runtimes.sh
install -m 644 /opt/cdb/factory/70-cdb-respeaker.rules /etc/udev/rules.d/70-cdb-respeaker.rules
/opt/cdb/runtime/bin/pip freeze > /opt/cdb/factory/python-packages.txt
dpkg-query -W > /opt/cdb/factory/os-packages.txt
groupadd -f cdb-network
usermod -aG cdb-network,audio,video,render,bluetooth cdb
passwd -l cdb
# No common password, admin user or broad sudo grant in the shipped image.
gpasswd -d cdb sudo || true
rm -f /etc/sudoers.d/010_pi-nopasswd
printf 'cdb ALL=(root) NOPASSWD: /usr/bin/systemctl reboot\n' > /etc/sudoers.d/cdb-reboot
chmod 440 /etc/sudoers.d/cdb-reboot
visudo -cf /etc/sudoers.d/cdb-reboot
install -m 644 /opt/cdb/factory/cdb-network.service /opt/cdb/factory/cdb-factory-init.service /etc/systemd/system/
install -m 644 /opt/cdb/factory/cdb-recorder-studio.service /opt/cdb/factory/cdb-recorder-agent.service /etc/systemd/user/
systemctl enable cdb-network.service cdb-factory-init.service
systemctl --global enable cdb-recorder-studio.service cdb-recorder-agent.service
systemctl disable ssh.service || true
mkdir -p /etc/lightdm/lightdm.conf.d /etc/xdg/autostart
printf '[Seat:*]\nautologin-user=cdb\nautologin-user-timeout=0\n' > /etc/lightdm/lightdm.conf.d/90-cdb.conf
printf '[Desktop Entry]\nType=Application\nName=Brain Studio\nExec=/opt/cdb/factory/kiosk.sh\nTerminal=false\n' > /etc/xdg/autostart/cdb-recorder.desktop
# pi-gen must not ask for a second user on top of our local setup flow.
rm -f /etc/xdg/autostart/piwiz.desktop
systemctl disable userconfig.service 2>/dev/null || true
rm -f /etc/ssh/ssh_host_* /var/lib/dbus/machine-id
: > /etc/machine-id
rm -f /.cdb-image-build
