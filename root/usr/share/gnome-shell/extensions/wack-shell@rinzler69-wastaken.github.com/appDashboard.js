import Clutter from 'gi://Clutter';
import Cogl from 'gi://Cogl';
import GObject from 'gi://GObject';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// Clip the composed preview, including wallpaper and window clones.
const RoundedPreview = GObject.registerClass(class InfinityRoundedPreview extends Clutter.ShaderEffect {
    vfunc_get_static_snippet() {
        // GNOME 51 uses Cogl snippets instead of shader_type/set_shader_source.
        // Apply the mask after the default fragment code has sampled the preview.
        return Cogl.Snippet.new(Cogl.SnippetHook.FRAGMENT, `
            uniform float width;
            uniform float height;
            uniform float radius;`, `
            vec2 size = vec2(width, height);
            vec2 p = cogl_tex_coord_in[0].xy * size;
            vec2 q = abs(p - size * 0.5) - (size * 0.5 - radius);
            float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
            float alpha = 1.0 - smoothstep(-0.75, 0.75, d);
            cogl_color_out *= alpha;`);
    }
});

export function isEmptyDashboardTarget(actor, controls) {
    if (!actor || !controls)
        return false;
    for (let node = actor; node; node = node.get_parent()) {
        if (node === controls._thumbnailsBox || node === controls.dash ||
            node === controls._searchEntry || node instanceof St.Button ||
            node instanceof St.Entry || node.can_focus || node._delegate?.app)
            return false;
        if (node === controls._appDisplay || node === controls)
            return true;
    }
    return false;
}

export default class AppDashboard {
    constructor() {
        this._previews = new Map();
        this._controls = Main.overview._overview?._controls;
        this._box = this._controls?._thumbnailsBox;
        this._box?.add_style_class_name('infinity-dashboard-previews');
        this._box?.connectObject('child-added', () => this._syncPreviews(), this);
        Main.overview.connectObject('shown', () => this._syncPreviews(), 'hidden', () => {
            this._press = null;
        }, this);
        global.stage.connectObject('captured-event', (_stage, event) => this._onEvent(event), this);
        this._syncPreviews();
    }

    _syncPreviews() {
        for (const actor of this._box?._thumbnails ?? []) {
            if (this._previews.has(actor))
                continue;
            const effect = new RoundedPreview();
            const update = () => {
                effect.set_uniform_value('width', Math.max(1, actor.width) + 0.0001);
                effect.set_uniform_value('height', Math.max(1, actor.height) + 0.0001);
                effect.set_uniform_value('radius', 12 * St.ThemeContext.get_for_stage(global.stage).scale_factor + 0.0001);
            };
            actor.add_effect_with_name('infinity-rounded-preview', effect);
            actor.connectObject('notify::width', update, 'notify::height', update,
                'destroy', () => this._previews.delete(actor), this);
            this._previews.set(actor, effect);
            update();
        }
    }

    _onEvent(event) {
        const controls = this._controls;
        if (!Main.overview.visible || !controls?.dash?.showAppsButton?.checked ||
            controls._appDisplay?._displayingDialog || controls._searchController?.searchActive) {
            this._press = null;
            return Clutter.EVENT_PROPAGATE;
        }
        const type = event.type();
        if (type !== Clutter.EventType.BUTTON_PRESS && type !== Clutter.EventType.BUTTON_RELEASE)
            return Clutter.EVENT_PROPAGATE;
        const [x, y] = event.get_coords();
        const actor = global.stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, x, y);
        const empty = event.get_button() === 1 && isEmptyDashboardTarget(actor, controls);
        if (type === Clutter.EventType.BUTTON_PRESS) {
            this._press = empty ? [x, y] : null;
            return Clutter.EVENT_PROPAGATE;
        }
        const press = this._press;
        this._press = null;
        if (empty && press && Math.hypot(x - press[0], y - press[1]) < 8) {
            Main.overview.hide();
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    destroy() {
        global.stage.disconnectObject(this);
        Main.overview.disconnectObject(this);
        this._box?.disconnectObject(this);
        this._box?.remove_style_class_name('infinity-dashboard-previews');
        for (const [actor, effect] of this._previews) {
            actor.disconnectObject(this);
            actor.remove_effect(effect);
        }
        this._previews.clear();
    }
}
