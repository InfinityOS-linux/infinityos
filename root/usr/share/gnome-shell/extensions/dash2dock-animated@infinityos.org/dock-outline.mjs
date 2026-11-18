// One Cairo contour avoids St's per-side border joins changing the lower arcs.
export function paintDockOutline(cr, width, height, radius = 0, thickness = 0, light = false, scale = 1) {
    const highlight = 1.75 * scale;
    const stroke = Math.max(0, thickness * scale);
    const inset = Math.max(stroke, highlight) / 2;
    const w = width - inset * 2, h = height - inset * 2;
    if (w <= 0 || h <= 0) return;
    const r = Math.max(0, Math.min(radius * scale - inset, w / 2, h / 2));
    const contour = () => {
        cr.newPath();
        cr.moveTo(inset + r, inset);
        cr.lineTo(inset + w - r, inset);
        cr.arc(inset + w - r, inset + r, r, -Math.PI / 2, 0);
        cr.lineTo(inset + w, inset + h - r);
        cr.arc(inset + w - r, inset + h - r, r, 0, Math.PI / 2);
        cr.lineTo(inset + r, inset + h);
        cr.arc(inset + r, inset + h - r, r, Math.PI / 2, Math.PI);
        cr.lineTo(inset, inset + r);
        cr.arc(inset + r, inset + r, r, Math.PI, Math.PI * 1.5);
        cr.closePath();
    };
    if (stroke > 0) {
        contour();
        cr.setSourceRGBA(...(light ? [1, 1, 1, .65] : [.87, .80, 1, .32]));
        cr.setLineWidth(stroke);
        cr.stroke();
    }
    // Keep the heavier top highlight wholly outside the lower corner region.
    cr.save();
    cr.rectangle(0, 0, width, Math.min(highlight * 1.5, height / 2));
    cr.clip();
    contour();
    cr.setSourceRGBA(...(light ? [70 / 255, 40 / 255, 100 / 255, .35]
        : [218 / 255, 199 / 255, 1, .55]));
    cr.setLineWidth(highlight);
    cr.stroke();
    cr.restore();
}
