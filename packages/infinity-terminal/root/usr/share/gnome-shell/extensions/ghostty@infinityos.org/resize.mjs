export function clampTerminalHeight(screenHeight, panelHeight, requestedHeight) {
    const available = Math.max(1, screenHeight - panelHeight);
    const minimum = Math.min(available, 96);
    return Math.min(available, Math.max(minimum, Math.round(requestedHeight)));
}

export function isFullHeight(screenHeight, panelHeight, height) {
    return height >= screenHeight - panelHeight - 8;
}
