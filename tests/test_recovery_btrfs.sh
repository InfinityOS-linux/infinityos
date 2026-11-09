#!/bin/bash
# Run only in a disposable privileged Fedora container with snapper and rpm-build.
set -euo pipefail
[[ -f /.dockerenv && $EUID -eq 0 ]] || exit 2
repo=$(cd "$(dirname "$0")/.." && pwd)
base=$(mktemp -d)
cleanup() { if [[ -f $base/mnt/root/var/lib/infinityos/offline-update.log ]]; then cat "$base/mnt/root/var/lib/infinityos/offline-update.log"; fi; umount "$base/boot" 2>/dev/null || true; umount -R "$base/mnt" 2>/dev/null || true; rm -rf "$base"; }
trap cleanup EXIT
truncate -s 6G "$base/disk.img"
mkfs.btrfs -q "$base/disk.img"
mkdir "$base/mnt"
mount -o loop "$base/disk.img" "$base/mnt"
top=$base/mnt
btrfs subvolume create "$top/root"
btrfs subvolume create "$top/var"
btrfs subvolume create "$top/home"
mkdir "$top/infinityos-roots"
target=$top/root
mount --bind "$target" "$target"
cp -a /usr /etc "$target/"
cp -a /var/. "$top/var/"
cp -a /bin /sbin /lib /lib64 "$target/"
mkdir -p "$target"/{dev,proc,run,tmp,sys,var,home}
mount --bind "$top/var" "$target/var"
mount --bind "$top/home" "$target/home"
mount --rbind /dev "$target/dev"
mount --make-rslave "$target/dev"
mount -t proc proc "$target/proc"
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
chroot "$target" snapper --no-dbus -c root create-config /
btrfs subvolume delete "$target/.snapshots"
btrfs subvolume create "$top/infinityos-snapshots"
mkdir "$target/.snapshots"
mount --bind "$top/infinityos-snapshots" "$target/.snapshots"
cat > "$target/usr/local/bin/snapper" <<WRAPPER
#!/bin/sh
exec $(command -v snapper) --no-dbus "\$@"
WRAPPER
cat > "$target/usr/local/bin/dnf" <<'WRAPPER'
#!/bin/sh
exec /usr/bin/dnf --disablerepo='*' "$@"
WRAPPER
chmod +x "$target/usr/local/bin/dnf"
# No service manager runs in this test chroot. Never reboot the container host.
cat > "$target/usr/local/bin/systemctl" <<'WRAPPER'
#!/bin/sh
if [ "$1" = is-active ]; then exit 1; fi
exit 0
WRAPPER
chmod +x "$target/usr/local/bin/"{snapper,systemctl}
cp "$repo"/root/usr/libexec/infinityos-backups-* "$target/usr/libexec/"
cp "$repo/root/usr/libexec/infinityos-refind-config" "$target/usr/libexec/"
cp "$repo"/root/usr/lib/systemd/system/infinityos-backups* "$target/usr/lib/systemd/system/"
mkdir -p "$target/usr/lib/kernel/install.d"
cp "$repo/root/usr/lib/kernel/install.d/96-infinityos-esp.install" "$target/usr/lib/kernel/install.d/"
cp "$repo"/packages/infinity-updater/root/usr/libexec/infinityos-* "$target/usr/libexec/"
mkdir -p "$target/usr/share/infinityos"
cp -a "$repo/packages/infinity-updater/root/usr/share/infinityos/updater" "$target/usr/share/infinityos/"
mkdir -p "$target/usr/lib/modules/$(uname -r)" "$target/etc/kernel" "$target/var/lib/infinityos"
touch "$target/var/lib/infinityos/backups-ready"
uuid=$(findmnt -n -o UUID -T "$top")
printf 'root=UUID=%s\n' "$uuid" > "$target/etc/kernel/cmdline"
printf 'UUID=%s / btrfs defaults 0 0\nUUID=%s /var btrfs subvol=var 0 0\nUUID=%s /home btrfs subvol=home 0 0\n' "$uuid" "$uuid" "$uuid" > "$target/etc/fstab"
# Build two real RPM versions with system and service data to roll back together.
mkdir -p "$base/rpmbuild"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
for version in 1 2; do
cat > "$base/rpmbuild/SPECS/test.spec" <<SPEC
Name: infinity-recovery-test
Version: $version
Release: 1
Summary: Recovery integration fixture
License: MIT
BuildArch: noarch
%description
Disposable recovery test package.
%install
mkdir -p %{buildroot}/usr/share/infinity-recovery-test %{buildroot}/var/lib/infinity-recovery-test
echo $version > %{buildroot}/usr/share/infinity-recovery-test/version
echo $version > %{buildroot}/var/lib/infinity-recovery-test/version
%files
/usr/share/infinity-recovery-test
/var/lib/infinity-recovery-test
SPEC
rpmbuild --define "_topdir $base/rpmbuild" -bb "$base/rpmbuild/SPECS/test.spec" > "$base/build.log" 2>&1
done
cp "$base/rpmbuild/RPMS/noarch/"*.rpm "$target/tmp/"
# Unsigned fixture packages are permitted only inside this disposable root.
mkdir -p "$target/etc/rpm"
printf '%%_pkgverify_level digest\n' > "$target/etc/rpm/macros.recovery-fixture"
chroot "$target" rpm -i /tmp/infinity-recovery-test-1-1.noarch.rpm
mkdir -p "$target/home/test"
echo before > "$target/home/test/document"
# Default systemd subvolumes, including a nested child and a path with spaces.
for path in lib/machines lib/portables 'lib/machines/test guest'; do
    mkdir -p "$(dirname "$target/var/$path")"
    rmdir "$target/var/$path" 2>/dev/null || true
    btrfs subvolume create "$target/var/$path"
    echo original > "$target/var/$path/data"
done
chroot "$target" /usr/libexec/infinityos-upgrade-system --local-rpm /tmp/infinity-recovery-test-2-1.noarch.rpm
[[ $(cat "$target/usr/share/infinity-recovery-test/version") == 1 ]]
chroot "$target" /usr/libexec/infinityos-offline-update
[[ $(cat "$target/usr/share/infinity-recovery-test/version") == 2 ]]
[[ $(cat "$target/var/lib/infinity-recovery-test/version") == 2 ]]
echo after > "$target/home/test/document"
for path in lib/machines lib/portables 'lib/machines/test guest'; do echo changed > "$target/var/$path/data"; done
number=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["snapshot"])' "$target/var/lib/infinityos/offline-update-result.json")
# Exercise the production restore function, without its interactive menu loop.
sed '/^while true; do/,$d' "$repo/root/usr/libexec/infinityos-backups-menu" > "$target/tmp/restore"
printf '\nrestore_snapshot %s\n' "$number" >> "$target/tmp/restore"
printf '\n' | chroot "$target" bash /tmp/restore
mkdir "$base/boot"
mount "$(findmnt -n -o SOURCE -T "$top" | cut -d '[' -f1)" "$base/boot"
restored=$base/boot
var_subvol=$(awk '$2 == "/var" { print $4 }' "$restored/etc/fstab" | sed 's/.*subvol=//')
[[ $(cat "$restored/usr/share/infinity-recovery-test/version") == 1 ]]
[[ $(cat "$top/$var_subvol/lib/infinity-recovery-test/version") == 1 ]]
[[ $(cat "$top/home/test/document") == after ]]
for path in lib/machines lib/portables 'lib/machines/test guest'; do
    [[ $(cat "$top/$var_subvol/$path/data") == original ]]
    btrfs subvolume show "$top/$var_subvol/$path" >/dev/null
done
[[ ! -e $restored/system-update && ! -L $restored/system-update ]]
umount "$base/boot"
# Anaconda may keep /var inside the root subvolume instead of mounting it separately.
umount "$target/var"
cp -a "$top/var/." "$target/var/"
# cp preserves data but not subvolume boundaries; recreate those boundaries.
for path in lib/machines lib/portables 'lib/machines/test guest'; do
    mv "$target/var/$path" "$target/var/$path.old"
    btrfs subvolume create "$target/var/$path"
    cp -a "$target/var/$path.old/." "$target/var/$path/"
    rm -rf "$target/var/$path.old"
done
sed -i '\| /var |d'  "$target/etc/fstab"
number=$(chroot "$target" /usr/libexec/infinityos-backups-snapshot 'Integrated /var test' | tail -1)
[[ -f $target/.snapshots/var-in-root-$number ]]
echo modified > "$target/var/lib/infinity-recovery-test/version"
echo later > "$target/var/lib/machines/test guest/data"
sed '/^while true; do/,$d' "$repo/root/usr/libexec/infinityos-backups-menu" > "$target/tmp/restore"
printf '\nrestore_snapshot %s\n' "$number" >> "$target/tmp/restore"
printf '\n' | chroot "$target" bash /tmp/restore
mount "$(findmnt -n -o SOURCE -T "$top" | cut -d '[' -f1)" "$base/boot"
[[ $(cat "$base/boot/var/lib/infinity-recovery-test/version") == 2 ]]
[[ $(cat "$base/boot/var/lib/machines/test guest/data") == changed ]]
btrfs subvolume show "$base/boot/var/lib/machines/test guest" >/dev/null
[[ $(cat "$top/home/test/document") == after ]]
umount "$base/boot"
# Config and the recovery menu share deletion of complete snapshot pairs.
chroot "$target" /usr/libexec/infinityos-backups-manage list > "$base/snapshots.json"
python3 -c 'import json,sys; rows=json.load(open(sys.argv[1])); assert rows["ready"] and all(r["complete"] for r in rows["snapshots"])' "$base/snapshots.json"
chroot "$target" /usr/libexec/infinityos-backups-manage delete "$number" > /dev/null
[[ ! -e $target/.snapshots/nested-$number && ! -e $target/.snapshots/$number/snapshot && ! -e $target/.snapshots/var-in-root-$number ]]
for companion in "$target"/.snapshots/var-[0-9]*; do
    [[ -d $companion ]] || continue
    id=${companion##*/var-}
    chroot "$target" /usr/libexec/infinityos-backups-manage delete "$id" > /dev/null
    [[ ! -e $target/.snapshots/nested-$id && ! -e $companion && ! -e $target/.snapshots/$id/snapshot ]]
done
echo 'PASS: real offline RPM update, separate and integrated /var restore, /home preserved, paired snapshot deletion.'
