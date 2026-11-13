'use strict';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import { tempPath, trySpawnCommandLine } from './utils.js';
// import { trySpawnCommandLine } from 'resource:///org/gnome/shell/misc/util.js';

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Graphene from 'gi://Graphene';

import { Clock } from './apps/clock.js';
import { Calendar } from './apps/calendar.js';

// sync with animator
const CANVAS_SIZE = 120;
const DEBOUNCE_CHECK_TIMEOUT = 750;

class ServiceCounter {
  constructor(name, interval, callback, advance) {
    advance = advance || 0;
    this.name = name;
    this._interval = interval;
    this._ticks = advance == -1 ? interval : advance;
    this._callback = callback;
  }

  update(elapsed) {
    this._ticks += elapsed;
    if (this._ticks >= this._interval) {
      this._ticks -= this._interval;
      if (this._callback) {
        this._callback();
      }
      return true;
    }
    return false;
  }
}

export const Services = class {
  constructor() {
    this._mounts = {};
    this._downloadsDir = Gio.File.new_for_path(
      GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) ||
      GLib.build_filenamev([GLib.get_home_dir(), 'Downloads'])
    );
  }

  enable() {
    this._mounts = {};
    this._services = [
      new ServiceCounter('trash', 1000 * 15, this.checkTrash.bind(this)),
      new ServiceCounter(
        'clock',
        1000 * 60, // every minute
        // 1000 * 1, // every second
        () => {
          this.extension.docks.forEach((d) => {
            d._onClock();
          });
        },
        -1
      ),
      new ServiceCounter(
        'calendar',
        1000 * 60 * 15,
        () => {
          this.extension.docks.forEach((d) => {
            d._onCalendar();
          });
        },
        -1
      ),
      new ServiceCounter(
        'ping',
        1000 * 5,
        () => {
          // deferred stuff is required when .desktop entry if first created
          // check for deferred mounts
          this._commitMounts();

          // notifications
          this.checkNotifications();
        },
        0
      ),
    ];

    this._disableNotifications = 0;

    this._volumeMonitor = Gio.VolumeMonitor.get();
    this._volumeMonitor.connectObject(
      'mount-added',
      this._onMountAdded.bind(this),
      'mount-removed',
      this._onMountRemoved.bind(this),
      this
    );

    this._trashDir = Gio.File.new_for_uri('trash:///');
    this._trashMonitor = this._trashDir.monitor(
      Gio.FileMonitorFlags.WATCH_MOVES,
      null
    );
    this._trashMonitor.connectObject(
      'changed',
      (fileMonitor, file, otherFile, eventType) => {
        switch (eventType) {
          case Gio.FileMonitorEvent.CHANGED:
          case Gio.FileMonitorEvent.CREATED:
          case Gio.FileMonitorEvent.MOVED_IN:
            return;
        }
        this.checkTrash();
      },
      this
    );

    this.setupDownloads();

    this._debounceCheckRecents();

    //! ***services startup function are blocking calls. async these***
    this.checkTrash();

    this.checkNotifications();

    this.checkMounts();
    this._commitMounts();
  }

  disable() {
    this._downloadsMonitor?.disconnectObject(this);
    this._downloadsMonitor = null;
    this._services = [];
    this._volumeMonitor?.disconnectObject(this);
    this._volumeMonitor = null;
    this._trashMonitor?.disconnectObject(this);
    this._trashMonitor = null;
    this._trashDir = null;
  }

  setupDownloads() {
    if (this._downloadsMonitor) {
      this._downloadsMonitor.disconnectObject(this);
      this._downloadsMonitor = null;
    }
    const xdgDownloads = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD);
    const downloadsPath = this.extension.downloads_path ||
      xdgDownloads || GLib.build_filenamev([GLib.get_home_dir(), 'Downloads']);
    this._downloadsDir = Gio.File.new_for_path(downloadsPath);
    try {
      this._downloadsDir.make_directory_with_parents(null);
    } catch (error) {
      if (!error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.EXISTS))
        throw error;
    }

    this._downloadsMonitor = this._downloadsDir.monitor(
      Gio.FileMonitorFlags.WATCH_MOVES,
      null
    );
    this._downloadsMonitor.connectObject(
      'changed',
      (fileMonitor, file, otherFile, eventType) => {
        switch (eventType) {
          case Gio.FileMonitorEvent.CHANGED:
          case Gio.FileMonitorEvent.CREATED:
          case Gio.FileMonitorEvent.MOVED_IN:
            return;
        }
        this._debounceCheckDownloads();
      },
      this
    );

    this._debounceCheckDownloads();
  }

  _commitMounts() {
    this.checkMounts();
  }

  _onMountAdded(_monitor, mount) {
    this.last_mounted = mount;
    this.checkMounts();
    this.extension.animate();
  }

  _onMountRemoved() {
    // A removed mount may already have lost its drive/name. Reconcile by URI.
    this.checkMounts();
    this.extension.animate();
  }

  _mountId(mount) {
    const uri = mount.get_root().get_uri();
    const id = GLib.compute_checksum_for_string(GLib.ChecksumType.SHA256, uri, -1);
    return tempPath(`mount-${id}-dash2dock-lite.desktop`);
  }

  update(elapsed) {
    this._services.forEach((s) => {
      s.update(elapsed);
    });
  }

  setupTrashIcon() {
    let extension_path = this.extension.path;
    let appname = `trash-dash2dock-lite.desktop`;
    let app_id = tempPath(appname);
    let fn = Gio.File.new_for_path(app_id);
    let open_app = 'nautilus --select';

    let trash_action = `${extension_path}/apps/empty-trash.sh`;
    {
      let fn = Gio.File.new_for_path('.local/share/Trash');
      trash_action = `rm -rf "${fn.get_path()}"`;
    }

    const binName = Gio.DesktopAppInfo.new_from_filename('/usr/share/infinityos/bin.desktop')?.get_name() ?? 'Bin';
    let content = `[Desktop Entry]\nVersion=1.0\nTerminal=false\nType=Application\nName=${binName}\nExec=${open_app} trash:///\nIcon=user-trash\nStartupWMClass=trash-dash2dock-lite\nActions=trash\n\n[Desktop Action trash]\nName=Empty Trash\nExec=${trash_action}\nTerminal=true\n`;
    const [, etag] = fn.replace_contents(
      content,
      null,
      false,
      Gio.FileCreateFlags.REPLACE_DESTINATION,
      null
    );
  }

  setupFolderIcon(name, title, icon, path) {
    // expand
    let full_path = Gio.file_new_for_path(path).get_path();
    let extension_path = this.extension.path;
    let appname = `${name}-dash2dock-lite.desktop`;
    let app_id = tempPath(appname);
    let fn = Gio.File.new_for_path(app_id);
    // let open_app = 'xdg-open';
    let open_app = 'nautilus --select';

    let content = `[Desktop Entry]\nVersion=1.0\nTerminal=false\nType=Application\nName=${title}\nExec=${open_app} ${full_path}\nIcon=${icon}\nStartupWMClass=${name}-dash2dock-lite\n`;
    const [, etag] = fn.replace_contents(
      content,
      null,
      false,
      Gio.FileCreateFlags.REPLACE_DESTINATION,
      null
    );
  }

  setupFolderIcons() {
    this.setupTrashIcon();
    const appId = tempPath('downloads-dash2dock-lite.desktop');
    const desktopFile = Gio.File.new_for_path(appId);
    desktopFile.replace_contents(
      '[Desktop Entry]\nVersion=1.0\nTerminal=false\nType=Application\nName=Downloads\nExec=/usr/libexec/infinityos-open-downloads\nIcon=/usr/share/infinityos/folder-icons/folder-download-dock.svg\nStartupWMClass=downloads-dash2dock-lite\n',
      null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null
    );
    this.setupFolderIcon(
      'documents',
      'Documents',
      '/usr/share/infinityos/folder-icons/folder-documents-dock.svg',
      'Documents'
    );
  }

  _toSafeFileName(name) {
    return name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9._-]/g, '_') // replace anything not allowed
      .replace(/_+/g, '_') // collapse multiple underscores
      .replace(/^_+|_+$/g, ''); // trim leading/trailing underscores
  }

  setupMountIcon(mount) {
    const mount_id = this._mountId(mount);
    const label = mount.get_name().replace(/[\r\n]/g, ' ');
    // Desktop Exec expands percent codes; preserve URI escapes as literal percent.
    const target = '"' + mount.get_root().get_uri()
      .replace(/["`$\\]/g, character => encodeURIComponent(character))
      .replace(/%/g, '%%') + '"';
    const icon = '/usr/share/infinityos/folder-icons/drive-dock.svg';
    let content = `[Desktop Entry]\nVersion=1.0\nTerminal=false\nType=Application\nName=${label}\nExec=gio open ${target}\nIcon=${icon}\n`;
    if (mount.can_unmount())
      content += `Actions=unmount;\n\n[Desktop Action unmount]\nName=Unmount\nExec=gio mount -u ${target}\n`;
    Gio.File.new_for_path(mount_id).replace_contents(
      content, null, false, Gio.FileCreateFlags.REPLACE_DESTINATION, null);
    this._mounts[mount_id] = mount;
  }

  checkNotifications() {
    if (this._disableNotifications > 4) return;

    let sources = Main.messageTray.getSources();
    this._appNotices = this._appNotices || {};

    Object.keys(this._appNotices).forEach((k) => {
      this._appNotices[k].previous = this._appNotices[k].count;
      this._appNotices[k].count = 0;
    });

    let app_map = {
      'org.gnome.Evolution-alarm-notify.desktop': 'org.gnome.Calendar.desktop',
    };

    sources.forEach((source) => {
      let appId = null;
      if (source.app) {
        appId = source.app.get_id();
      }
      if (!appId && source._app) {
        appId = source._app.get_id();
      }
      if (!appId) {
        appId = source._appId;
      }
      if (!appId) {
        appId = '?';
      }

      // remap
      appId = app_map[appId] || appId;

      if (!this._appNotices[appId]) {
        this._appNotices[appId] = {
          count: 0,
          previous: 0,
          urgency: 0,
          source: source,
        };
      }
      this._appNotices[appId].count = source.count;
      this._appNotices[`${appId}`] = this._appNotices[appId];
      if (!appId.endsWith('desktop')) {
        this._appNotices[`${appId}.desktop`] = this._appNotices[appId];
      }
    });

    let hasUpdates = false;
    Object.keys(this._appNotices).forEach((k) => {
      if (this._appNotices[k].previous != this._appNotices[k].count) {
        hasUpdates = true;
      }
    });

    let update = {};
    Object.keys(this._appNotices).forEach((k) => {
      if (this._appNotices[k].count > 0) {
        update[k] = this._appNotices[k];
      }
    });
    this._appNotices = update;

    if (hasUpdates) {
      this.extension.animate();
    }
  }

  checkTrash() {
    if (!this.extension.trash_icon) return;

    let iter = this._trashDir.enumerate_children(
      'standard::*',
      Gio.FileQueryInfoFlags.NONE,
      null
    );
    let prev = this.trashFull;
    this.trashFull = iter.next_file(null) != null;
    if (prev != this.trashFull) {
      this.extension.animate({ refresh: true });
    }
    return this.trashFull;
  }

  async checkRecentFilesInFolder(path) {
    console.log(`checking ${path}`);
    let maxs = [5, 8, 10, 12, 15, 20, 25];
    let max_recent_items = maxs[this.extension.max_recent_items || 0];
    let downloadFiles = [];
    let downloadFilesLength = 0;

    let directory = Gio.File.new_for_path(path);
    let enumerator = directory.enumerate_children(
      [
        Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE,
        Gio.FILE_ATTRIBUTE_STANDARD_NAME,
        Gio.FILE_ATTRIBUTE_STANDARD_ICON,
        Gio.FILE_ATTRIBUTE_TIME_MODIFIED,
      ].join(','),
      Gio.FileQueryInfoFlags.NONE,
      null
    );

    let fileInfo;
    while ((fileInfo = enumerator.next_file(null)) !== null) {
      let fileName = fileInfo.get_name();
      let fileModified = fileInfo.get_modification_time();

      let icon = 'file';
      if (fileInfo.get_icon() && fileInfo.get_icon().names) {
        icon =
          this.extension.lookup_icon_from_names(fileInfo.get_icon().names) ??
          icon;
      }

      downloadFiles.push({
        index: 0,
        name: fileName,
        display: fileName,
        icon: icon,
        type: fileInfo.get_content_type(),
        path: [path, fileName].join('/'),
        date: fileModified ?? { tv_sec: 0 },
        fileInfo: fileInfo,
      });
    }

    downloadFilesLength = downloadFiles.length;
    downloadFiles.sort((a, b) => {
      return a.date.tv_sec > b.date.tv_sec ? -1 : 1;
    });

    let index = 0;
    downloadFiles.forEach((f) => {
      f.index = index++;
    });

    downloadFiles.splice(max_recent_items);
    // console.log(downloadFiles);

    return Promise.resolve([downloadFiles, downloadFilesLength]);
  }

  /*
  async _checkRecentFilesInFolder(path) {
    console.log(`checking ${path}`);
    let maxs = [5, 10, 15, 20, 25];
    let max_recent_items = maxs[this.extension.max_recent_items || 0];

    let downloadFiles = [];
    let downloadFilesLength = 0;
    try {
      let [res, pid, in_fd, out_fd, err_fd] = GLib.spawn_async_with_pipes(
        null,
        ['/bin/ls', '-1t', `${path}`],
        null,
        0,
        null
      );

      let out_reader = new Gio.DataInputStream({
        base_stream: new Gio.UnixInputStream({ fd: out_fd }),
      });

      let idx = 0;
      for (let i = 0; i < 100 && idx < 30; i++) {
        let [line, size] = out_reader.read_line_utf8(null);
        if (line == null) break;
        // const res =
        //   /\s([a-zA-Z]{3})\s{1,3}([0-9]{1,3})\s{1,3}([0-9:]{4,8})\s{1,3}(.*)/.exec(
        //     line
        //   );
        // if (res) {
        let fileName = line.trim();
        const fileStat = {
          name: fileName,
        };
        if (fileStat.name && (fileStat.name == '.' || fileStat.name == '..'))
          continue;
        fileStat.index = idx++;

        const file = Gio.File.new_for_path(`Downloads/${fileName}`);
        const fileInfo = file.query_info(
          'standard::*,unix::uid',
          Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS,
          null
        );

        if (file && fileInfo && fileStat.index < max_recent_items) {
          downloadFiles.push({
            index: fileStat.index,
            name: fileStat.name,
            display: fileInfo.get_display_name(),
            path: file.get_path(),
            icon: this.extension.lookup_icon_from_names(fileInfo.get_icon().get_names()) ?? 'file',
            type: fileInfo.get_content_type(),
            date: fileStat.date ?? '',
          });
        }
        downloadFilesLength++;
        // }
      }
    } catch (err) {
      console.log(err);
    }

    return [downloadFiles, downloadFilesLength];
  }
  */

  async checkRecentFilesFromRecentManager() {
    console.log('checking recent manager');
    let maxs = [5, 8, 10, 12, 15, 20, 25];
    let max_recent_items = maxs[this.extension.max_recent_items || 0];

    let recentFiles = [];
    let recentFilesLength = 0;

    try {
      await trySpawnCommandLine(
        `/usr/bin/env -S gjs -m "${this.extension.path}/apps/recents.js"`
      );
    } catch (err) {
      console.log(err);
    }

    // const recentsPath = tempPath('recents.txt');
    const recentsPath = '/tmp/recents.txt';

    let fn = Gio.File.new_for_path(recentsPath);
    if (fn.query_exists(null)) {
      try {
        const [success, contents] = await fn.load_contents_async(null);
        const decoder = new TextDecoder();
        let contentsString = decoder.decode(contents);
        let idx = 0;
        let lines = contentsString.split('\n');
        lines.forEach((l) => {
          let res = l.split('|');
          if (res.length != 2) return;
          const file = Gio.File.new_for_path(res[0]);
          if (!file.query_exists(null)) {
            console.log('not exists');
            return;
          }
          if (recentFiles.length < max_recent_items) {
            const fileStat = {
              index: idx++,
              name: file.get_basename(),
              icon: res[1],
              // icon: this.extension.lookup_icon_from_names([res[1]]) ?? 'file',
              path: file.get_path(),
              type: 'file',
            };
            recentFiles.push(fileStat);
          }
          recentFilesLength++;
        });
      } catch (err) {
        console.log(err);
      }
    }

    return Promise.resolve([recentFiles, recentFilesLength]);
  }

  async checkRecents() {
    // NOT YET READY
    // try {
    //   [this._recentFiles, this._recentFilesLength] =
    //     await this.checkRecentFilesFromRecentManager();
    // } catch (err) {
    //   console.log(err);
    // }
  }

  _debounceCheckRecents() {
    if (this.extension._loTimer) {
      if (!this._debounceCheckSeq) {
        this._debounceCheckSeq = this.extension._loTimer.runDebounced(
          () => {
            this.checkRecents();
          },
          DEBOUNCE_CHECK_TIMEOUT,
          'debounceCheckRecents'
        );
      } else {
        this.extension._loTimer.runDebounced(this._debounceCheckSeq);
      }
    }
  }

  async checkDownloads() {
    try {
      let path = this._downloadsDir.get_path();
      [this._downloadFiles, this._downloadFilesLength] =
        await this.checkRecentFilesInFolder(path);
    } catch (err) {
      console.log(err);
    }
  }

  _debounceCheckDownloads() {
    if (this.extension._loTimer) {
      if (!this._debounceCheckSeq) {
        this._debounceCheckSeq = this.extension._loTimer.runDebounced(
          () => {
            this.checkDownloads();
          },
          DEBOUNCE_CHECK_TIMEOUT,
          'debounceCheckDownloads'
        );
      } else {
        this.extension._loTimer.runDebounced(this._debounceCheckSeq);
      }
    }
  }

  _getMountName(mount) {
    let name = null;
    if (mount.get_drive()) {
      name = mount.get_drive().get_name();
    }

    if (!name) {
      if (mount.get_volume()) {
        name = mount.get_volume().get_name();
      }
    }

    if (!name) {
      if (mount.get_default_location()) {
        name = mount.get_default_location().get_basename();
      }
    }

    return name || 'Volume';
  }

  checkMounts() {
    const mounts = this.extension.mounted_icon ? this._volumeMonitor.get_mounts() : [];
    const active = new Set(mounts.map(mount => this._mountId(mount)));
    for (const id of Object.keys(this._mounts)) {
      if (!active.has(id)) {
        delete this._mounts[id];
        try { Gio.File.new_for_path(id).delete(null); } catch (_error) { /* Already removed. */ }
      }
    }
    for (const mount of mounts) {
      if (!this._mounts[this._mountId(mount)])
        this.setupMountIcon(mount);
    }
    this.mounts = mounts;
  }

  //! this is out of place - services should only do background process - no rendering
  updateIcon(item, settings) {
    if (!item) {
      return;
    }
    let icon = item._icon;
    if (!icon || !icon.icon_name) {
      return;
    }

    let { scaleFactor, iconSize, dock } = settings;

    // todo move dots and badges here?

    // the trash
    if (this.extension.trash_icon && icon.icon_name.startsWith('user-trash')) {
      let new_icon = this.trashFull ? 'user-trash-full' : 'user-trash';
      if (new_icon != icon.icon_name) {
        icon.icon_name = new_icon;
      }
    }

    // clock
    if (icon.icon_name == 'org.gnome.clocks') {
      if (this.extension.clock_icon) {
        let clock = item._clock;
        if (!clock) {
          clock = new Clock(CANVAS_SIZE, dock.extension._widgetStyle);
          dock._clock = clock;
          item._clock = clock;
          item._image = clock;
          // item._appwell.first_child.add_child(clock);
          dock.renderArea.add_child(clock);
        }
        if (clock) {
          clock._icon = icon;
          clock.width = item._renderer.width * item._renderer.scaleX;
          clock.height = clock.width;
          // let toScale = item._scale;
          // clock.set_scale(toScale, toScale);
          let canvasScale = clock.width / (clock._canvas.width + 2);
          clock._canvas.set_scale(canvasScale, canvasScale);
          clock.x = item._renderer.x;
          clock.y = item._renderer.y;
          clock.opacity = item._renderer.opacity;
          clock.show();
          item._renderer.opacity = clock.shouldHideIcon() ? 0 : 255;
        }
      } else {
        let clock = item._clock;
        item._icon.visible = true;
        clock?.hide();
      }
    }

    // calender
    if (icon.icon_name == 'org.gnome.Calendar') {
      if (this.extension.calendar_icon) {
        let calendar = item._calendar;
        if (!calendar) {
          calendar = new Calendar(CANVAS_SIZE, dock.extension._widgetStyle);
          dock._calendar = calendar;
          item._calendar = calendar;
          item._image = calendar;
          dock.renderArea.add_child(calendar);
        }
        if (calendar) {
          calendar._icon = icon;
          calendar.width = item._renderer.width * item._renderer.scaleX;
          calendar.height = calendar.width;
          // let toScale = item._scale;
          // calendar.set_scale(toScale, toScale);
          let canvasScale = calendar.width / (calendar._canvas.width + 2);
          calendar._canvas.set_scale(canvasScale, canvasScale);
          calendar.x = item._renderer.x;
          calendar.y = item._renderer.y;
          calendar.opacity = item._renderer.opacity;
          calendar.show();
          item._renderer.opacity = calendar.shouldHideIcon() ? 0 : 255;
        }
      } else {
        let calendar = item._calendar;
        item._icon.visible = true;
        calendar?.hide();
      }
    }
  }
};
