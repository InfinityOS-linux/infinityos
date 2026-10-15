#!/bin/bash
# Run as root on Linux with btrfs-progs and loop devices.
set -euo pipefail

image=$(mktemp /var/tmp/infinityos-btrfs-test.XXXXXX)
mountdir=$(mktemp -d)
loopdev=
cleanup() {
	if mountpoint -q "$mountdir"; then umount "$mountdir"; fi
	if [[ -n $loopdev ]]; then losetup -d "$loopdev"; fi
	rm -f "$image"
	rmdir "$mountdir"
}
trap cleanup EXIT

truncate -s 256M "$image"
mkfs.btrfs -q -f "$image"
loopdev=$(losetup --find --show "$image")
mount "$loopdev" "$mountdir"
btrfs subvolume create "$mountdir/root" >/dev/null
btrfs subvolume create "$mountdir/root/.snapshots" >/dev/null
printf 'before\n' > "$mountdir/root/probe"
btrfs subvolume snapshot -r "$mountdir/root" "$mountdir/root/.snapshots/1" >/dev/null
mv "$mountdir/root/.snapshots" "$mountdir/infinityos-snapshots"
mkdir "$mountdir/root/.snapshots"
btrfs subvolume snapshot "$mountdir/infinityos-snapshots/1" "$mountdir/restored" >/dev/null
printf 'after\n' > "$mountdir/restored/probe"
root_id=$(btrfs inspect-internal rootid "$mountdir/restored")
btrfs subvolume set-default "$root_id" "$mountdir"
umount "$mountdir"
mount "$loopdev" "$mountdir"
[[ $(cat "$mountdir/probe") == after ]]
mount -o subvol=infinityos-snapshots "$loopdev" "$mountdir/.snapshots"
[[ $(cat "$mountdir/.snapshots/1/probe") == before ]]
umount "$mountdir/.snapshots"
umount "$mountdir"
mount -o subvolid=5 "$loopdev" "$mountdir"
[[ -f $mountdir/infinityos-snapshots/1/probe ]]
echo 'Btrfs restore and persistent snapshot catalog: OK'
