import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {test} from 'node:test';
const source = readFileSync(new URL('./run_shell_smoke.sh', import.meta.url), 'utf8');
const cleanup = source.slice(source.indexOf('cleanup() {'), source.indexOf('\ntrap cleanup EXIT'));
for (const [name, failures, original, expected] of [
    ['retries a service teardown race', 2, 0, 0],
    ['does not hide a failed smoke test', 2, 7, 7],
    ['reports persistent cleanup failures', 99, 0, 1],
]) {
    test(name, () => {
        const result = spawnSync('bash', ['-c', `set -eu
sandbox=/unused
attempts=0
mountpoint() { return 1; }
sleep() { :; }
rm() { attempts=$((attempts + 1)); test "$attempts" -gt "$FAILURES"; }
${cleanup}
trap cleanup EXIT
exit "$ORIGINAL"
`], {encoding: 'utf8', env: {...process.env, FAILURES: String(failures), ORIGINAL: String(original)}});
        assert.equal(result.status, expected, result.stderr);
    });
}
