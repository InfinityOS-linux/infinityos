import Atk from 'gi://Atk';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import St from 'gi://St';
import Shell from 'gi://Shell';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';

export function createWarpButton(extensionPath) {
    const button = new PanelMenu.Button(0.0, 'Warp', true);
    button.accessible_role = Atk.Role.PUSH_BUTTON;
    button.add_child(new St.Icon({
        gicon: Gio.icon_new_for_string(`${extensionPath}/icons/warp-symbolic.svg`),
        style_class: 'system-status-icon',
    }));
    const activate = () => {
        const app = Shell.AppSystem.get_default().lookup_app('app.drey.Warp.desktop');
        if (app)
            app.activate();
        else
            Main.notifyError('Warp', 'app.drey.Warp is not installed.');
    };
    const click = new Clutter.ClickGesture();
    click.set_recognize_on_press(true);
    click.connect('recognize', activate);
    button.add_action(click);
    button.connect('key-press-event', (_actor, event) => {
        if (![Clutter.KEY_Return, Clutter.KEY_KP_Enter, Clutter.KEY_space].includes(event.get_key_symbol()))
            return Clutter.EVENT_PROPAGATE;
        activate();
        return Clutter.EVENT_STOP;
    });
    return button;
}
