export const needsRightSide = (panelWidth, leftWidth, centerWidth) =>
    leftWidth + 12 > (panelWidth - centerWidth) / 2;
