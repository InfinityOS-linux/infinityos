import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {InjectionManager} from 'resource:///org/gnome/shell/extensions/extension.js';

function hasFiles() {
    if (GLib.get_user_name() === 'liveuser') return false;
    const folder = Gio.File.new_for_path(`/home/.infinityos-ramdrives/${new Gio.Credentials().get_unix_user()}`);
    let children;
    try {
        const info = folder.query_info('standard::type', Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
        if (info.get_file_type() !== Gio.FileType.DIRECTORY) return true;
        children = folder.enumerate_children('standard::name', Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
        return children.next_file(null) !== null;
    } catch (error) {
        return !error.matches?.(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND);
    } finally {
        children?.close(null);
    }
}

function runHelper(action) {
    const process = Gio.Subprocess.new(['/usr/libexec/infinityos-ramdrive', action],
        Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
    return new Promise((resolve, reject) => {
        process.communicate_utf8_async(null, null, (source, result) => {
            try {
                const [, , stderr] = source.communicate_utf8_finish(result);
                if (!source.get_successful()) throw new Error(stderr.trim() || 'RAMDrive operation failed.');
                resolve();
            } catch (error) {
                reject(error);
            }
        });
    });
}

export default class RamdriveRestart {
    constructor(dialog = Main.endSessionDialog, occupied = hasFiles, run = runHelper) {
        this.dialog = dialog;
        this.occupied = occupied;
        this.run = run;
        this.active = false;
        this.busy = false;
        this.epoch = 0;
        this.buttons = [];
        this.manager = new InjectionManager();
        const owner = this;
        this.confirm = dialog._confirm;
        this.manager.overrideMethod(dialog, '_updateButtons', original => function (...args) {
            if ([2, 3].includes(this._type) && owner.occupied()) {
                owner.activate();
                return;
            }
            owner.reset();
            return original.apply(this, args);
        });
        this.manager.overrideMethod(dialog, '_sync', original => function (...args) {
            const result = original.apply(this, args);
            if (owner.active) owner.sync();
            return result;
        });
        this.manager.overrideMethod(dialog, '_startTimer', original => function (...args) {
            if (owner.active) { this._stopTimer(); return; }
            return original.apply(this, args);
        });
        this.manager.overrideMethod(dialog, '_confirm', original => async function (signal) {
            // Covers countdown and alternate reboot entry points as well.
            if (signal === 'ConfirmedReboot' && (owner.active || owner.occupied())) {
                if (!owner.active) owner.activate();
                owner.sync();
                this.open();
                return;
            }
            return original.call(this, signal);
        });
        this.closedId = dialog.connect('closed', () => this.reset());
        this.openedId = dialog.connect('opened', () => this.position());
        this.keyController = new Clutter.KeyController();
        this.keyId = this.keyController.connect('key-press', () => {
            const [, symbol] = this.keyController.get_key();
            if (!this.active || symbol !== Clutter.KEY_Escape)
                return Clutter.EVENT_PROPAGATE;
            if (!this.busy) dialog.cancel();
            return Clutter.EVENT_STOP;
        });
        dialog.dialogLayout.add_action(this.keyController);
    }

    text(english, polish) {
        return GLib.get_language_names().some(language => language.startsWith('pl')) ? polish : english;
    }

    activate() {
        if (this.active) return;
        this.active = true;
        this.status = '';
        this.dialog._stopTimer();
        this.dialog._stopAltCapture();
        this.dialog._altCapture.enabled = false;
        const layout = this.dialog.dialogLayout._dialog;
        const wrapper = this.dialog.dialogLayout;
        this.outerLayout = {};
        for (const key of ['x_align', 'y_align', 'margin_top', 'margin_right', 'margin_left'])
            this.outerLayout[key] = wrapper[key];
        wrapper.x_align = Clutter.ActorAlign.END;
        wrapper.y_align = Clutter.ActorAlign.START;
        wrapper.margin_top = Main.panel.height + 16;
        wrapper.margin_right = wrapper.margin_left = 16;
        this.layout = {};
        for (const key of ['x_align', 'y_align', 'margin_top', 'margin_right', 'margin_left', 'width', 'translation_x', 'translation_y'])
            this.layout[key] = layout[key];
        layout.x_align = Clutter.ActorAlign.END;
        layout.y_align = Clutter.ActorAlign.START;
        layout.margin_top = layout.margin_right = layout.margin_left = 0;
        const monitor = Main.layoutManager.monitors[global.display.get_current_monitor()];
        layout.width = Math.min(440, monitor.width - 32);
        layout.add_style_class_name('infinity-ramdrive-restart');
        this.positionId = layout.connect('notify::allocation', () => this.position());
        this.dialog.clearButtons();
        this.buttons = [
            this.dialog.addButton({label: this.text('Remove & Restart', 'Usuń i uruchom ponownie'),
                action: () => { this.prepare('clear'); }}),
            this.dialog.addButton({label: this.text('Save files', 'Zapisz pliki'),
                action: () => { this.prepare('save'); }}),
        ];
        this.dialog.setInitialKeyFocus(this.buttons[1]);
    }

    sync() {
        this.dialog._messageDialogContent.title = this.text(
            'There are files in your RAMDrive.', 'W RAMDrive znajdują się pliki.');
        this.dialog._messageDialogContent.description = this.status || this.text(
            'Save files moves them to Desktop/Saved Files, then restarts. Press Esc to cancel.',
            'Zapisz pliki przeniesie je do folderu Saved Files na pulpicie, a następnie uruchomi komputer ponownie. Esc anuluje.');
        this.position();
    }

    position() {
        if (!this.active) return;
        const layout = this.dialog.dialogLayout._dialog;
        const [width] = layout.get_transformed_size();
        if (width <= 0) return;
        const [x, y] = layout.get_transformed_position();
        const monitor = Main.layoutManager.monitors[global.display.get_current_monitor()];
        // GNOME's nested modal bins may center their natural allocation even
        // with end alignment. Position the final actor in stage coordinates.
        layout.translation_x += monitor.x + monitor.width - width - 16 - x;
        layout.translation_y += monitor.y + Main.panel.height + 16 - y;
    }

    async prepare(action) {
        if (!this.active || this.busy) return;
        const epoch = this.epoch;
        this.busy = true;
        this.buttons.forEach(button => { button.reactive = button.can_focus = false; });
        this.status = action === 'save'
            ? this.text('Saving files…', 'Zapisywanie plików…')
            : this.text('Removing files…', 'Usuwanie plików…');
        this.sync();
        try {
            await this.run(action);
            if (epoch !== this.epoch) return;
            if (this.occupied()) throw new Error(this.text(
                'RAMDrive still contains files. Check them and try again.',
                'RAMDrive nadal zawiera pliki. Sprawdź je i spróbuj ponownie.'));
            // Keep GNOME's update checkbox, other-session checks and reboot signal.
            await this.confirm.call(this.dialog, 'ConfirmedReboot');
        } catch (error) {
            if (epoch !== this.epoch) return;
            this.status = this.text('Restart stopped. ', 'Restart zatrzymany. ') + error.message;
            this.busy = false;
            this.buttons.forEach(button => { button.reactive = button.can_focus = true; });
            this.sync();
        }
    }

    reset() {
        this.epoch++;
        this.active = this.busy = false;
        this.buttons = [];
        if (this.layout) {
            this.dialog.dialogLayout._dialog.disconnect(this.positionId);
            Object.assign(this.dialog.dialogLayout._dialog, this.layout);
            this.dialog.dialogLayout._dialog.remove_style_class_name('infinity-ramdrive-restart');
            this.layout = null;
        }
        if (this.outerLayout) {
            Object.assign(this.dialog.dialogLayout, this.outerLayout);
            this.outerLayout = null;
        }
    }

    destroy() {
        if (this.active) this.dialog.cancel();
        this.reset();
        this.manager.clear();
        this.dialog.disconnect(this.closedId);
        this.dialog.disconnect(this.openedId);
        this.keyController.disconnect(this.keyId);
        this.dialog.dialogLayout.remove_action(this.keyController);
    }
}
