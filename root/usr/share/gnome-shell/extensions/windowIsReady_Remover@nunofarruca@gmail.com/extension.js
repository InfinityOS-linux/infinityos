import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class WindowIsReadyRemover {
    enable() {
        const handler = Main.windowAttentionHandler;
        if (!handler || this._handler)
            return;

        // GNOME owns both urgency handlers through this object.
        global.display.disconnectObject(handler);
        this._handler = handler;

        // Other shell code can still create a window-attention source. Keep it
        // out of the tray while leaving every other notification untouched.
        const addSource = Main.messageTray.add;
        this._addSource = function (source) {
            if (source?.constructor?.name === 'WindowAttentionSource')
                return;

            return addSource.call(this, source);
        };
        this._originalAddSource = addSource;
        Main.messageTray.add = this._addSource;
    }

    disable() {
        const handler = this._handler;
        if (!handler)
            return;

        if (Main.messageTray.add === this._addSource)
            Main.messageTray.add = this._originalAddSource;
        this._addSource = null;
        this._originalAddSource = null;

        global.display.connectObject(
            'window-demands-attention', handler._onWindowDemandsAttention.bind(handler),
            'window-marked-urgent', handler._onWindowDemandsAttention.bind(handler),
            handler);
        this._handler = null;
    }
}
