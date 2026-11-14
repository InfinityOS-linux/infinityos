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

export function uniqueMetrics(ids, metrics) {
    const seen = new Set();
    return ids.filter(id => {
        const key = resolveMetric(id, metrics).id;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

export function toggleMetric(ids, id, metrics) {
    const key = resolveMetric(id, metrics).id;
    const matches = candidate => resolveMetric(candidate, metrics).id === key;
    return ids.some(matches) ? ids.filter(candidate => !matches(candidate)) : uniqueMetrics([...ids, id], metrics);
}

export function dropMetric(ids, source, target, after) {
    if (source === target || !ids.includes(source) || !ids.includes(target)) return ids;
    const result = ids.filter(id => id !== source);
    result.splice(result.indexOf(target) + (after ? 1 : 0), 0, source);
    return result;
}

export class Stopwatch {
    constructor(now) { this.now = now; this.elapsed = 0; this.started = null; }
    get running() { return this.started !== null; }
    get seconds() { return this.elapsed + (this.running ? this.now() - this.started : 0); }
    toggle() {
        if (this.running) { this.elapsed = this.seconds; this.started = null; }
        else this.started = this.now();
    }
    reset() { this.elapsed = 0; this.started = null; }
    get text() {
        const total = Math.floor(this.seconds);
        return [Math.floor(total / 3600), Math.floor(total / 60) % 60, total % 60]
            .map(value => String(value).padStart(2, '0')).join(':');
    }
}

export class Countdown {
    constructor(now, pomodoro = false) {
        this.now = now; this.pomodoro = pomodoro; this.minutes = pomodoro ? 25 : 5;
        this.reset();
    }
    get running() { return this.deadline !== null; }
    get seconds() { return Math.max(0, this.running ? this.deadline - this.now() : this.remaining); }
    get text() { const seconds = Math.ceil(this.seconds); return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`; }
    toggle() {
        if (this.running) { this.remaining = this.seconds; this.deadline = null; }
        else { if (!this.remaining) this.reset(); this.deadline = this.now() + this.remaining; }
    }
    reset(minutes = this.minutes) {
        this.minutes = minutes; this.remaining = minutes * 60; this.deadline = null; this.phase = 'work'; this.rounds = 0;
    }
    finish() {
        if (!this.running || this.seconds > 0) return null;
        if (!this.pomodoro) { this.remaining = 0; this.deadline = null; return 'done'; }
        if (this.phase === 'work') {
            this.rounds++; this.phase = 'break'; this.remaining = (this.rounds % 4 === 0 ? 15 : 5) * 60;
        } else { this.phase = 'work'; this.remaining = 25 * 60; }
        this.deadline = this.now() + this.remaining;
        return this.phase;
    }
}

export function networkTotals(text) {
    let rx = 0, tx = 0;
    for (const line of text.split('\n')) {
        const colon = line.indexOf(':');
        if (colon < 0 || line.slice(0, colon).trim() === 'lo') continue;
        const fields = line.slice(colon + 1).trim().split(/\s+/).map(Number);
        if (fields.length >= 16 && Number.isFinite(fields[0]) && Number.isFinite(fields[8])) {
            rx += fields[0]; tx += fields[8];
        }
    }
    return {rx, tx};
}

export function networkRate(previous, current, elapsed) {
    if (!previous || elapsed <= 0) return {rx: 0, tx: 0};
    return {rx: Math.max(0, current.rx - previous.rx) / elapsed,
        tx: Math.max(0, current.tx - previous.tx) / elapsed};
}
