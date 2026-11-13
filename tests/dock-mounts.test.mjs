import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {test} from 'node:test';
import vm from 'node:vm';

const source = readFileSync(new URL('../root/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/services.js', import.meta.url), 'utf8')
  .replace(/^import .*;\n/gm, '').replace('export const Services', 'const Services');
function fixture() {
  const files = new Map();
  const prototype = vm.runInNewContext(`${source}\nServices.prototype`, {
    tempPath: name => `/tmp/${name}`,
    Gio: {FileCreateFlags: {REPLACE_DESTINATION: 0}, File: {new_for_path: path => ({
      replace_contents: content => files.set(path, content), delete: () => files.delete(path),
    })}},
    GLib: {ChecksumType: {SHA256: 0}, compute_checksum_for_string: (_type, text) => createHash('sha256').update(text).digest('hex')},
  });
  const service = Object.create(prototype);
  service._mounts = {};
  service.extension = {mounted_icon: true, animate() {}};
  let mounts = [];
  service._volumeMonitor = {get_mounts: () => mounts};
  return {service, files, setMounts: value => { mounts = value; }};
}
const mount = (uri, name = 'Disk', removable = true) => ({
  get_name: () => name, get_root: () => ({get_uri: () => uri}), can_unmount: () => removable,
});

test('unmount removes stale icons even when the removed device loses its name', () => {
  const {service, files, setMounts} = fixture();
  const a = mount('file:///media/PRO%20STORAGE');
  const b = mount('file:///media/DVD');
  setMounts([a,b]); service.checkMounts();
  assert.equal(Object.keys(service._mounts).length, 2);
  setMounts([a]); service._onMountRemoved(null, {get_name() { throw Error('Device is gone'); }});
  service._commitMounts();
  assert.equal(Object.keys(service._mounts).length, 1);
  assert.equal(files.size, 1);
  assert.equal(Object.values(service._mounts)[0], a);
});

test('identical volume labels remain independent and periodic refresh repairs missed events', () => {
  const {service, setMounts} = fixture();
  setMounts([mount('file:///media/a'), mount('file:///media/b')]); service.checkMounts();
  assert.equal(Object.keys(service._mounts).length, 2);
  setMounts([]); service._commitMounts();
  assert.equal(Object.keys(service._mounts).length, 0);
});

test('mount actions use GIO and quote URI escapes; fixed mounts have no unmount action', () => {
  const {service, files, setMounts} = fixture();
  setMounts([mount('file:///media/PRO%20STORAGE'), mount('file:///media/fixed', 'Fixed', false)]);
  service.checkMounts();
  const [removable, fixed] = [...files.values()];
  assert.match(removable, /Exec=gio mount -u "file:\/\/\/media\/PRO%%20STORAGE"/);
  assert.doesNotMatch(removable, /Exec=umount/);
  assert.doesNotMatch(fixed, /Actions=|Name=Unmount/);
});
