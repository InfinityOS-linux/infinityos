const UPDATER = 'org.infinityos.Updater';

function isUpdaterWindow(window) {
  for (let owner = window; owner; owner = owner.get_transient_for?.()) {
    if (owner.get_gtk_application_id?.() === UPDATER || owner.get_wm_class?.() === UPDATER)
      return true;
  }
  return false;
}

export function excludeFromDock(app) {
  if (!app) return false;
  if (app.get_id?.() === UPDATER + '.desktop') return true;
  const windows = app.get_windows?.() ?? [];
  // Window-backed helpers have no launcher. Regular unregistered GUI apps still
  // belong in the dock as soon as Mutter has a task window for them.
  if (!windows.length) return Boolean(app.is_window_backed?.());
  return windows.every(window => isUpdaterWindow(window) ||
    (app.is_window_backed?.() && (window.skip_taskbar || window.is_override_redirect?.())));
}
