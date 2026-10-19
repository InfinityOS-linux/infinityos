"""GSettings mapping for Infinity Config's percentage sliders."""

DOCK_SCHEMA = "org.gnome.shell.extensions.dash2dock-lite"
DOCK_SCHEMA_DIR = "/usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/schemas"
CURSOR_SCHEMA = "org.gnome.desktop.interface"
DOCK_DEFAULT = 0.21428571428571427
CURSOR_DEFAULT = 24


def slider_to_percent(position):
    """Place 100% at the physical midpoint while spanning 20–200%."""
    position = max(0, min(100, round(position)))
    return round(20 + position * 1.6) if position <= 50 else 2 * position


def percent_to_slider(percent):
    percent = max(20, min(200, percent))
    return (percent - 20) / 1.6 if percent <= 100 else percent / 2


def dock_size(percent):
    return DOCK_DEFAULT * percent / 100


def cursor_size(percent):
    return max(1, round(CURSOR_DEFAULT * percent / 100))


def dock_percent(value):
    return max(20, min(200, round(value / DOCK_DEFAULT * 100)))


def cursor_percent(value):
    return max(20, min(200, 5 * round(value / CURSOR_DEFAULT * 20)))
