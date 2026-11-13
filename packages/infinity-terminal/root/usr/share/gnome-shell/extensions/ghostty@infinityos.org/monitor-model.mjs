export const defaultMetrics = ['auto:cpu-temp', 'auto:gpu-temp', 'cpu:clock', 'auto:cpu-power', 'cpu:tdp', 'memory:used', 'disk:/'];

export function resolveMetric(id, metrics, tdp = 0) {
    if (id === 'cpu:tdp')
        return {id, label: 'CPU TDP', group: 'System (manual)', value: tdp > 0 ? tdp : null, unit: 'W'};
    const automatic = {
        'auto:cpu-temp': ['CPU Temp', '°C'],
        'auto:gpu-temp': ['GPU Temp', '°C'],
        'auto:cpu-power': ['CPU Power', 'W'],
    }[id];
    if (automatic) {
        return metrics.find(m => m.label.startsWith(automatic[0]) && !m.label.includes('Limit')) ??
            {id, label: automatic[0], value: null, unit: automatic[1]};
    }
    return metrics.find(m => m.id === id) ?? {id, label: id, value: null, unit: ''};
}

export function formatMetric(metric, fahrenheit = false) {
    if (!Number.isFinite(metric.value)) return 'N/A';
    let {value, unit} = metric;
    if (unit === '°C' && fahrenheit) { value = value * 9 / 5 + 32; unit = '°F'; }
    const digits = ['GHz', 'GiB'].includes(unit) ? 1 : 0;
    const maximum = Number.isFinite(metric.maximum) ? ` / ${metric.maximum.toFixed(digits)}` : '';
    return `${value.toFixed(digits)}${maximum} ${unit}`;
}

export function appendSample(history, value, limit) {
    return [...history, Number.isFinite(value) ? value : null].slice(-limit);
}

export function moveMetric(ids, index, delta) {
    const result = [...ids];
    const target = index + delta;
    if (index >= 0 && index < result.length && target >= 0 && target < result.length)
        [result[index], result[target]] = [result[target], result[index]];
    return result;
}
