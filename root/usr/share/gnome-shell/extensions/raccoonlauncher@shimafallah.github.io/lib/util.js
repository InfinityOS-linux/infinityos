// Lightweight fuzzy matcher. Returns a score (higher = better),
// or -1 when the query does not match the target at all.
export function fuzzyScore(query, target) {
    if (!query)
        return 0;

    query = query.toLowerCase();
    target = (target || '').toLowerCase();

    if (target === query)
        return 1000;
    if (target.startsWith(query))
        return 800 - (target.length - query.length);

    const idx = target.indexOf(query);
    if (idx !== -1)
        return 600 - idx - (target.length - query.length);

    // Subsequence match with a bonus for consecutive characters.
    let qi = 0;
    let score = 0;
    let lastMatch = -2;
    for (let ti = 0; ti < target.length && qi < query.length; ti++) {
        if (target[ti] === query[qi]) {
            score += lastMatch === ti - 1 ? 5 : 1;
            lastMatch = ti;
            qi++;
        }
    }

    if (qi === query.length)
        return 200 + score - target.length * 0.1;

    return -1;
}

