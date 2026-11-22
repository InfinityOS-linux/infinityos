import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
const read = path => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');
const source = read('scripts/verify-infinity-iso');
const start = source.indexOf('    gamescope_release=');
const check = source.slice(start, source.indexOf('\nfi', start));
test('x64 image requests the exact patched Gamescope built by the RPM workflow', () => {
  const spec = read('packages/gamescope/gamescope.spec');
  const version = spec.match(/^Version:\s+(\S+)/m)[1];
  const release = spec.match(/^Release:\s+(\S+)/m)[1].replace('%{?dist}', '.fc45');
  const packages = read('teams/workstation.xml');
  assert.ok(packages.includes(`<package name="gamescope-${version}-${release}.x86_64" arch="x86_64"/>`));
  assert.ok(packages.includes('<package name="gamescope" arch="aarch64"/>'));
  assert.ok(check.includes(`${version}-${release}.x86_64`));
});
test('ISO verification accepts the patched RPM and rejects upstream, missing and duplicate packages', () => {
  for (const [release, status, ok] of [
    ['3.16.31-2.infinityos.fc45.x86_64', 0, true],
    ['3.16.31-1.fc45.x86_64', 0, false],
    ['package gamescope is not installed', 1, false],
    ['3.16.31-2.infinityos.fc45.x86_64\n3.16.31-1.fc45.i686', 0, false],
  ]) {
    const result = spawnSync('bash', ['-c', `set -eu\nrootpoint=/unused\nrpm() { printf '%s\\n' "$TEST_RELEASE"; return "$TEST_STATUS"; }\n${check}`], {
      env: { ...process.env, TEST_RELEASE: release, TEST_STATUS: String(status) }, encoding: 'utf8',
    });
    assert.equal(result.status === 0, ok, result.stderr);
    if (!ok && status === 0) assert.ok(result.stderr.includes(release));
  }
});
