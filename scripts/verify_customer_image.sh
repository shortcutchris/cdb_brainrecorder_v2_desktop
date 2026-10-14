#!/bin/bash
# Offline validation inside a dedicated privileged Linux build container.
# Accepts a regular .img file only; never opens a physical SD device.
set -euo pipefail
[[ $# == 1 && -f $1 && ! -b $1 && $1 == *.img ]] || { echo 'Usage: verify_customer_image.sh REGULAR_FILE.img'; exit 2; }
[[ $(uname -s) == Linux && $(id -u) == 0 ]] || { echo 'Use the isolated Linux image builder as root'; exit 2; }
image=$(realpath -- "$1")
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
workspace=$(mktemp -d /tmp/cdb-image-audit.XXXXXX)
loop=''
cleanup() {
  umount "$workspace/root" 2>/dev/null || true
  umount "$workspace/boot" 2>/dev/null || true
  [[ -z $loop ]] || losetup -d "$loop"
  rmdir "$workspace/root" "$workspace/boot" "$workspace" 2>/dev/null || true
}
trap cleanup EXIT
mkdir "$workspace/root" "$workspace/boot"
loop=$(losetup --find --show --read-only --partscan "$image")
# Docker Desktop may expose partition numbers through sysfs without device nodes.
for partition in 1 2; do
  path="${loop}p${partition}"
  if [[ ! -b $path ]]; then
    IFS=: read -r major minor < "/sys/class/block/$(basename "$path")/dev"
    mknod "$path" b "$major" "$minor"
  fi
done
fsck.fat -n "${loop}p1"
e2fsck -fn "${loop}p2"
mount -o ro "${loop}p1" "$workspace/boot"
mount -o ro,noload "${loop}p2" "$workspace/root"
python3 "$script_dir/audit_customer_rootfs.py" "$workspace/root"
test -s "$workspace/boot/config.txt"
test -s "$workspace/boot/cmdline.txt"
test -s "$workspace/boot/kernel_2712.img"
test -s "$workspace/boot/bcm2712-rpi-5-b.dtb"
for file in opt/cdb/runtime/bin/python opt/cdb/source/web_server.py opt/cdb/source/studio/welcome.html usr/bin/labwc-pi usr/bin/chromium usr/bin/paplay usr/bin/parec usr/bin/nmcli; do
  # Absolute symlinks belong to the target root, not the host root.
  test -e "$workspace/root/$file" || test -L "$workspace/root/$file"
done
test -f "$workspace/root/etc/lightdm/lightdm.conf.d/90-cdb.conf"
test -L "$workspace/root/etc/systemd/system/multi-user.target.wants/cdb-factory-init.service"
test -L "$workspace/root/etc/systemd/system/multi-user.target.wants/cdb-network.service"
test -L "$workspace/root/etc/systemd/user/default.target.wants/cdb-recorder-studio.service"
if [[ -L "$workspace/root/etc/systemd/system/multi-user.target.wants/ssh.service" ]]; then
  echo 'SSH unexpectedly enabled'; exit 1
fi
printf 'Offline image validation passed. Hardware boot test still required.\n'
sha256sum "$image"
