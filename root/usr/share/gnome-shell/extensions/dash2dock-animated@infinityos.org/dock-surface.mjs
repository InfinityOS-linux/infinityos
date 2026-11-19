const PANEL_LAYERS = new Set(['wackPanelBackdrop', 'wackPanelBackdropOverlay', 'wackPanelProximityOverlay']);

function rgba(actor) {
    const color = actor.get_theme_node().get_background_color();
    return typeof color.get_red === 'function'
        ? [color.get_red(), color.get_green(), color.get_blue(), color.get_alpha()]
        : [color.red / 255, color.green / 255, color.blue / 255, color.alpha / 255];
}

export function dockSurfaceLayers(panel, light, blurReady) {
    if (!blurReady) return [light ? [250 / 255, 247 / 255, 1, 1] : [24 / 255, 22 / 255, 36 / 255, 1]];
    const layers = [rgba(panel)];
    for (const actor of panel.get_children()) {
        if (!PANEL_LAYERS.has(actor.name) || !actor.visible) continue;
        const color = rgba(actor);
        color[3] *= actor.opacity / 255;
        layers.push(color);
    }
    return layers;
}

export function paintDockSurface(cr, width, height, radius, layers, scale = 1) {
    if (width <= 0 || height <= 0) return;
    const r = Math.max(0, Math.min(radius * scale, width / 2, height / 2));
    cr.save();
    cr.newPath();
    cr.moveTo(r, 0); cr.lineTo(width - r, 0);
    cr.arc(width - r, r, r, -Math.PI / 2, 0);
    cr.lineTo(width, height - r); cr.arc(width - r, height - r, r, 0, Math.PI / 2);
    cr.lineTo(r, height); cr.arc(r, height - r, r, Math.PI / 2, Math.PI);
    cr.lineTo(0, r); cr.arc(r, r, r, Math.PI, Math.PI * 1.5);
    cr.closePath(); cr.clip();
    for (const color of layers) {
        if (color[3] <= 0) continue;
        cr.setSourceRGBA(...color);
        cr.paint();
    }
    cr.restore();
}
