import assert from 'node:assert/strict';
import test from 'node:test';
import {appendSample, defaultMetrics, formatMetric, moveMetric, resolveMetric} from
    '../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/monitor-model.mjs';

test('selected GPU identity is preserved across enumeration and disconnection', () => {
    const a = {id: 'nvidia:GPU-a:temp', label: 'GPU Temp A', value: 54, unit: '°C'};
    const b = {id: 'nvidia:GPU-b:temp', label: 'GPU Temp B', value: 48, unit: '°C'};
    assert.equal(resolveMetric(a.id, [b, a]), a);
    assert.equal(resolveMetric(a.id, [b]).value, null);
    assert.equal(formatMetric(resolveMetric(a.id, [b])), 'N/A');
    assert.equal(resolveMetric('auto:gpu-temp', [b, a]), b);
});

test('temperatures, memory, zero and unknown values format without inventing data', () => {
    assert.equal(formatMetric({value: 0, unit: '°C'}, true), '32 °F');
    assert.equal(formatMetric({value: 12, maximum: 32, unit: 'GiB'}), '12.0 / 32.0 GiB');
    assert.equal(formatMetric({value: null, unit: 'W'}), 'N/A');
    assert.equal(formatMetric({value: NaN, unit: 'W'}), 'N/A');
    assert.equal(resolveMetric('cpu:tdp', [], 105).value, 105);
    assert.equal(resolveMetric('cpu:tdp', [], 0).value, null);
});

test('history is bounded and missing readings create gaps', () => {
    assert.deepEqual(appendSample([1, 2, 3], null, 3), [2, 3, null]);
    assert.deepEqual(appendSample([1, null], 0, 3), [1, null, 0]);
});

test('reordering preserves sensor selections and handles first/last boundaries', () => {
    const ids = ['a', 'b', 'c'];
    assert.deepEqual(moveMetric(ids, 1, -1), ['b', 'a', 'c']);
    assert.deepEqual(moveMetric(ids, 0, -1), ids);
    assert.deepEqual(moveMetric(ids, 2, 1), ids);
    assert.deepEqual(ids, ['a', 'b', 'c']);
    assert.ok(defaultMetrics.includes('memory:used'));
});
