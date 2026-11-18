import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import { CUPERTINO_PROMPT_VERTICAL_FRACTION } from './constants.js';

const NOTIF_MIN_TOP_MARGIN_FRACTION = 0.1;
const MESSAGE_PROMPT_GAP = 48;
const SWITCH_USER_MARGIN = 24;

export const WackLayout = GObject.registerClass(
class WackLayout extends Clutter.LayoutManager {
    _init(extension, stack, notifications, switchUserButton, messageContainer = null) {
        super._init();
        this._extension = extension;
        this._stack = stack;
        this._notifications = notifications;
        this._switchUserButton = switchUserButton;
        this._messageContainer = messageContainer;
    }

    vfunc_get_preferred_width(_container, forHeight) {
        return this._stack.get_preferred_width(forHeight);
    }

    vfunc_get_preferred_height(_container, forWidth) {
        return this._stack.get_preferred_height(forWidth);
    }

    vfunc_allocate(container, box) {
        const [width, height] = box.get_size();
        
        const [, , stackWidth, stackHeight] = this._stack.get_preferred_size();
        const [, , notifWidth, notifHeight] = this._notifications.get_preferred_size();

        // Allocate notifications with independent width to prevent auth prompt stretching
        const notifBox = new Clutter.ActorBox();
        const classic = this._extension._lockscreenMode !== 'cupertino';
        const clockBottom = classic
            ? this._extension._clockLayoutManager?.getClockBottom(height) ?? 0
            : 0;
        // Notifications yield space to authentication, never push its avatar
        // into the clock on short displays.
        const promptTop = classic ? clockBottom + 24 : height * NOTIF_MIN_TOP_MARGIN_FRACTION;
        const maxNotifHeight = Math.max(0, Math.min(notifHeight,
            height - promptTop - stackHeight - SWITCH_USER_MARGIN));
        
        notifBox.x1 = Math.floor((width - notifWidth) / 2.0);
        notifBox.y1 = height - maxNotifHeight;
        notifBox.x2 = notifBox.x1 + notifWidth;
        notifBox.y2 = notifBox.y1 + maxNotifHeight;
        this._notifications.allocate(notifBox);

        // Allocate authentication prompt stack
        const stackBox = new Clutter.ActorBox();
        let stackY;

        if (this._extension._lockscreenMode === 'cupertino') {
            // Use content size: the previous allocation can grow during authentication.
            const userWell = this._extension._cupertinoRestPrompt?._userWell;
            const [, , , preferredH] = userWell?.get_preferred_size() ?? [0, 0, 0, 0];
            const wellH = preferredH > 0 ? preferredH : 96;

            const anchorH = Math.floor(wellH * 1.3);
            // Keep multi-line authentication errors above the bottom edge.
            stackY = Math.max(0, Math.min(
                Math.floor(height * CUPERTINO_PROMPT_VERTICAL_FRACTION) - anchorH,
                height - stackHeight - SWITCH_USER_MARGIN
            ));
        } else {
            // Center the complete avatar/password group, not its top edge.
            // Reserve the actual clock bounds, including theme/font scaling.
            const availableBottom = height - maxNotifHeight - SWITCH_USER_MARGIN;
            stackY = Math.max(0, Math.min(
                Math.max(Math.floor((height - stackHeight) / 2), clockBottom + 24),
                availableBottom - stackHeight
            ));
        }

        stackBox.x1 = Math.floor((width - stackWidth) / 2.0);
        stackBox.y1 = stackY;
        stackBox.x2 = stackBox.x1 + stackWidth;
        stackBox.y2 = stackY + stackHeight;
        this._stack.allocate(stackBox);

        if (this._messageContainer && this._messageContainer.visible) {
            let msgW = this._extension._lockscreenMessageWidth ?? 0;
            let msgH = this._extension._lockscreenMessageHeight ?? 0;

            if (msgW <= 0 || msgH <= 0) {
                if (this._extension._messageManager) {
                    this._extension._messageManager.syncLayout();
                }
                msgW = this._extension._lockscreenMessageWidth ?? 0;
                msgH = this._extension._lockscreenMessageHeight ?? 0;
            }

            if (msgW > 0 && msgH > 0) {
                const msgBox = new Clutter.ActorBox();

                msgBox.x1 = Math.floor((width - msgW) / 2.0);
                msgBox.y1 = stackY - MESSAGE_PROMPT_GAP - msgH;
                msgBox.x2 = msgBox.x1 + msgW;
                msgBox.y2 = msgBox.y1 + msgH;

                this._messageContainer.allocate(msgBox);
            }
        }

        // Allocate switch user button if present
        if (this._switchUserButton?.visible) {
            const [, , natWidth, natHeight] = this._switchUserButton.get_preferred_size();
            const switchBox = new Clutter.ActorBox();
            const isRTL = this._switchUserButton.get_text_direction() === Clutter.TextDirection.RTL;

            switchBox.x1 = isRTL ? box.x1 + SWITCH_USER_MARGIN : box.x2 - natWidth - SWITCH_USER_MARGIN;
            switchBox.y1 = box.y2 - natHeight - SWITCH_USER_MARGIN;
            switchBox.x2 = switchBox.x1 + natWidth;
            switchBox.y2 = switchBox.y1 + natHeight;
            
            this._switchUserButton.allocate(switchBox);
        }
    }
});
