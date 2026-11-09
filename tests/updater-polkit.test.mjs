import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {test} from 'node:test';
let authorize;
runInNewContext(readFileSync(new URL('../packages/infinity-updater/root/usr/share/polkit-1/rules.d/49-infinityos-updater.rules', import.meta.url), 'utf8'), {
    polkit: {addRule: rule => { authorize = rule; }, Result: {YES: 'yes'}},
});
const subject = {local: true, active: true, isInGroup: group => group === 'wheel'};
function action(program, command = program) {
    return {id: 'org.freedesktop.policykit.exec', lookup: key => ({program, command_line: command})[key]};
}
test('active local administrators can run updater helpers and exact update commands', () => {
    for (const program of ['/usr/libexec/infinityos-upgrade-system', '/usr/libexec/infinityos-upgrade-release'])
        assert.equal(authorize(action(program), subject), 'yes');
    assert.equal(authorize(action('/usr/bin/flatpak', '/usr/bin/flatpak update --system --noninteractive --assumeyes'), subject), 'yes');
    assert.equal(authorize(action('/usr/bin/fwupdmgr', '/usr/bin/fwupdmgr update --assume-yes --no-reboot-check'), subject), 'yes');
});
test('non-admin, inactive and remote sessions do not receive passwordless authorization', () => {
    for (const restriction of [{local: false}, {active: false}, {isInGroup: () => false}])
        assert.equal(authorize(action('/usr/libexec/infinityos-upgrade-system'), {...subject, ...restriction}), undefined);
});
test('other programs, actions and Flatpak/firmware operations are not authorized', () => {
    for (const program of ['/bin/sh', '/usr/bin/dnf', '/tmp/infinityos-upgrade-system', '/usr/bin/flatpak', '/usr/bin/fwupdmgr'])
        assert.equal(authorize(action(program), subject), undefined);
    assert.equal(authorize({...action('/usr/libexec/infinityos-upgrade-system'), id: 'other'}, subject), undefined);
    assert.equal(authorize(action('/usr/bin/flatpak', '/usr/bin/flatpak uninstall --system --noninteractive --assumeyes'), subject), undefined);
});
