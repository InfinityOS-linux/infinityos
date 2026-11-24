const INTERNAL_APPS = new Set(['org.infinityos.updater', 'org.infinityos.steamboot']);
const SCRIPT_WINDOW = /^(?:sh|bash|dash|zsh|fish|ksh|gjs(?:-console)?|(?:org\.gnome\.)?zenity|yad|infinityos-[\w-]+|[^/]+\.sh)$/i;
const TASK_WINDOW_TYPES = new Set([0, 3, 4]); // Meta.WindowType.NORMAL, DIALOG, MODAL_DIALOG

function identities(window) {
  return [window.get_gtk_application_id?.(), window.get_wm_class?.(), window.get_wm_class_instance?.()];
}

function isInternal(id) {
  return INTERNAL_APPS.has(id?.toLowerCase().replace(/\.desktop$/, ''));
}

function isScript(id) {
  return Boolean(id && SCRIPT_WINDOW.test(id.split('/').at(-1)));
}

function isInternalWindow(window) {
  for (let owner = window; owner; owner = owner.get_transient_for?.()) {
    if (identities(owner).some(isInternal)) return true;
  }
  return false;
}

function isDockWindow(window, windowBacked) {
  if (window.skip_taskbar || window.is_override_redirect?.() || window.get_transient_for?.())
    return false;
  const type = window.get_window_type?.();
  if (type !== undefined && !TASK_WINDOW_TYPES.has(type))
    return false;
  const ids = identities(window);
  return !ids.some(isInternal) && !(windowBacked && ids.some(isScript));
}

export function dockWindows(app) {
  const windowBacked = app?.is_window_backed?.();
  if (isInternal(app?.get_id?.()) || (windowBacked && isScript(app?.get_name?.()))) return [];
  return (app?.get_windows?.() ?? []).filter(window => isDockWindow(window, windowBacked));
}

export function excludeFromDock(app, favorite = false) {
  if (!app) return false;
  if (isInternal(app.get_id?.())) return true;
  const windowBacked = app.is_window_backed?.();
  if (windowBacked && isScript(app.get_name?.())) return true;

  const windows = app.get_windows?.() ?? [];
  // Keep registered favorites and their launch animation when they are closed.
  // A window-backed entry is only useful when it has a real task window.
  if (!windows.length) return Boolean(windowBacked);
  if (favorite) return windows.every(isInternalWindow);
  return !windows.some(window => isDockWindow(window, windowBacked));
}
