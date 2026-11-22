"""Keep GTK surfaces opaque until their matching GNOME Shell backdrop is ready."""

from gi.repository import Gio, GLib


class PanelBackdrop:
    CSS = b"""
window.infinity-window.shell-backdrop box.infinity-shade { background: rgba(14, 10, 20, 0.22); }
window.infinity-window.shell-backdrop box.infinity-card {
  background: rgba(24, 22, 36, 0.52); background-image: none;
  box-shadow: 0 16px 50px rgba(0, 0, 0, 0.3);
}
window.infinity-window.shell-backdrop.light-mode box.infinity-shade { background: rgba(32, 24, 45, 0.10); }
window.infinity-window.shell-backdrop.light-mode box.infinity-card { background: rgba(250, 247, 255, 0.74); }
"""

    def __init__(self, window, ready_property):
        self.window = window
        self.ready_property = ready_property
        self.proxy = None
        self.signals = ()
        self.cancel = Gio.Cancellable()
        window.connect("unrealize", self._disconnect)
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
            "org.gnome.Shell", "/org/infinityos/UpdaterBackdrop",
            "org.infinityos.UpdaterBackdrop", self.cancel, self._connected)

    def _connected(self, _source, result):
        try:
            proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except GLib.Error:
            return
        if self.cancel.is_cancelled():
            return
        self.proxy = proxy
        self.signals = (
            proxy.connect("g-properties-changed", self._sync),
            proxy.connect("notify::g-name-owner", self._sync),
        )
        self._sync()

    def _sync(self, *_args):
        value = None
        try:
            if self.proxy.get_name_owner():
                value = self.proxy.get_cached_property(self.ready_property)
        except GLib.Error:
            pass
        if value is not None and value.unpack() is True:
            self.window.add_css_class("shell-backdrop")
        else:
            self.window.remove_css_class("shell-backdrop")

    def _disconnect(self, *_args):
        self.cancel.cancel()
        if self.proxy:
            for signal in self.signals:
                self.proxy.disconnect(signal)
            self.proxy = None
        self.window.remove_css_class("shell-backdrop")
