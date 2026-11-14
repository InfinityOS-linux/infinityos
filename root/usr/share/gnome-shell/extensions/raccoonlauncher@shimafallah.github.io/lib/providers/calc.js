import St from 'gi://St';

// Inline calculator. Evaluates basic arithmetic without using eval(),
// via a small recursive-descent parser.
export class CalcProvider {
    query(text) {
        const expr = text.trim();
        if (expr.length > 2048) return [];

        // Must look like a math expression: only safe characters,
        // and contain at least one operator and one digit.
        if (!/^[-+*/%^().\d\s]+$/.test(expr))
            return [];
        if (!/[-+*/%^]/.test(expr) || !/\d/.test(expr))
            return [];

        let value;
        try {
            value = evaluate(expr);
        } catch {
            return [];
        }
        if (value === null || !isFinite(value))
            return [];

        const str = formatNumber(value);
        return [{
            id: 'calc',
            name: str,
            description: `= ${expr}   (Enter to copy)`,
            iconName: 'accessories-calculator-symbolic',
            score: 2000,
            activate: () => {
                St.Clipboard.get_default()
                    .set_text(St.ClipboardType.CLIPBOARD, str);
            },
        }];
    }
}

function formatNumber(n) {
    // Trim floating-point noise like 0.30000000000000004.
    return String(Number(n.toPrecision(12)));
}

// Grammar (exponent binds tighter than unary minus, so -2^2 = -4):
//   expr   := term  (('+' | '-') term)*
//   term   := unary (('*' | '/' | '%') unary)*
//   unary  := ('-' | '+') unary | power
//   power  := primary ('^' unary)?      (right-associative)
//   primary:= number | '(' expr ')'
function evaluate(input) {
    const s = input.replace(/\s+/g, '');
    let pos = 0;

    const peek = () => s[pos];

    function parseExpr() {
        let v = parseTerm();
        while (peek() === '+' || peek() === '-') {
            const op = s[pos++];
            const r = parseTerm();
            v = op === '+' ? v + r : v - r;
        }
        return v;
    }

    function parseTerm() {
        let v = parseUnary();
        while (peek() === '*' || peek() === '/' || peek() === '%') {
            const op = s[pos++];
            const r = parseUnary();
            if (op === '*')
                v *= r;
            else if (op === '/')
                v /= r;
            else
                v %= r;
        }
        return v;
    }

    function parseUnary() {
        if (peek() === '-') {
            pos++;
            return -parseUnary();
        }
        if (peek() === '+') {
            pos++;
            return parseUnary();
        }
        return parsePower();
    }

    function parsePower() {
        const base = parsePrimary();
        if (peek() === '^') {
            pos++;
            return Math.pow(base, parseUnary());
        }
        return base;
    }

    function parsePrimary() {
        if (peek() === '(') {
            pos++;
            const v = parseExpr();
            if (peek() !== ')')
                throw new Error('expected )');
            pos++;
            return v;
        }
        let num = '';
        while (pos < s.length && /[0-9.]/.test(s[pos]))
            num += s[pos++];
        if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(num))
            throw new Error('expected number');
        return Number(num);
    }

    const result = parseExpr();
    if (pos !== s.length)
        throw new Error('unexpected trailing input');
    return result;
}

