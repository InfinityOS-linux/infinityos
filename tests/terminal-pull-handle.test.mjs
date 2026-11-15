import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
const source = readFileSync(new URL('../packages/infinity-terminal/root/usr/share/gnome-shell/extensions/ghostty@infinityos.org/pull-handle.js', import.meta.url), 'utf8').replace(/^import .*;\n/gm, '').replace('export class', 'class');
function fixture() {
    let fullscreen = false, toggle = 0, shown = 0, hidden = 0, grabs = 0, dismissed = 0;
    const signal = {connect() { return 1; }, disconnect() {}};
    const drawing = [];
    const cr = new Proxy({}, {get: (_, key) => (...args) => drawing.push([key, ...args])});
    const actor = {translation_y: 0, remove_all_transitions() {}, ease(values) { this.translation_y = values.translation_y; values.onComplete?.(); }};
    const window = {minimized: true, get_frame_rect: () => ({height:500}), get_compositor_private: () => actor};
    const terminal = {_indicator: {}, _findWindow: () => window, _toggle() {toggle++;},
        _showTerminal() {shown++; window.minimized = false;}, _hide() {hidden++;},
        _monitor: () => ({height:1000}), _topInset: () => 30, _settings: {set_double(k,v) {terminal.savedHeight=v*1000;}}, _place() {}, _offscreenOffset: () => -500, _syncResizeHandle() {}};
    const Main = {panel: {...signal, statusArea: {dateMenu: {...signal, get_transformed_position: () => [700, 0], get_transformed_size: () => [100, 32]}},
        get_transformed_position: () => [0, -52], get_transformed_size: () => [1500, 32], get_theme_node: () => ({get_background_color: () => ({red: 11, green: 9, blue: 18, alpha: 255})})},
        layoutManager: {...signal, primaryMonitor: {index: 0, y: 0}, addTopChrome() {}, removeChrome() {}}, overview: {...signal, visible: false}, sessionMode: {...signal, isLocked: false}};
    const context = {GLib: {PRIORITY_DEFAULT: 0, timeout_add: () => 1, Source: {remove() {}}}, Main, Atk: {Role: {PUSH_BUTTON: 1}}, console,
        St: {DrawingArea: class {constructor() {Object.assign(this, signal); this.visible = true;} contains(a) {return a === this;} set_size(w,h) {this.width=w;this.height=h;} set_position(x,y) {this.x=x;this.y=y;} queue_repaint() {} get_context() {return cr;} get_surface_size() {return [180,18];} hide() {this.visible=false;} destroy() {}}, ThemeContext: {get_for_stage: () => ({scale_factor: 1})}, Settings: {get: () => ({enable_animations: true})}},
        Clutter: {EventType: {BUTTON_PRESS: 1, BUTTON_RELEASE: 2, MOTION: 3, KEY_PRESS: 4}, ModifierType: {BUTTON1_MASK: 1}, KEY_Escape: 27, KEY_Return: 13, KEY_space: 32, EVENT_STOP: true, EVENT_PROPAGATE: false, AnimationMode: {EASE_OUT_CUBIC: 1}},
        global: {display: {...signal, get_monitor_in_fullscreen: () => fullscreen}, stage: {...signal, get_event_actor: () => handle.actor, grab() {grabs++;return {dismiss() {dismissed++;}};}}}, terminal};
    const handle = vm.runInNewContext(`${source}\nnew TerminalPullHandle(terminal)`,context);
    const event = (type,y,held=1,key=0) => handle.event({type:()=>type,get_coords:()=>[750,y],get_button:()=>1,get_state:()=>held,get_key_symbol:()=>key});
    return {handle,terminal,actor,window,drawing,Main,event,get toggle(){return toggle;},get shown(){return shown;},get hidden(){return hidden;},get balanced(){return grabs===dismissed;},fullscreen(value){fullscreen=value;handle.sync();}};
}
test('symmetric curve is centered under clock without reserving desktop space',()=>{
    const f=fixture();assert.equal(f.handle.actor.x,660);assert.equal(f.handle.actor.y,31);f.handle.paint();
    const curves=f.drawing.filter(x=>x[0]==='curveTo');assert.equal(curves.length,2);
    assert.deepEqual(Array.from(curves[0].slice(1)),[32,0,48,17,78,17]);
    assert.deepEqual(Array.from(curves[1].slice(1)),[132,17,148,0,180,0]);
    assert.equal(f.drawing.at(-1)[0],'$dispose');
});
test('click toggles once; drag follows pointer and settles open',()=>{
    const f=fixture();f.event(1,40);f.event(2,40);assert.equal(f.toggle,1);
    f.event(1,40);f.event(3,240);assert.equal(f.shown,1);assert.equal(f.actor.translation_y,-300);
    f.event(2,240);assert.equal(f.actor.translation_y,0);assert.equal(f.terminal.savedHeight,200);assert.equal(f.toggle,1);assert(f.balanced);
});
test('short pull and Escape cancel; cold-start cancellation clears pending show',()=>{
    const f=fixture();f.event(1,40);f.event(3,60);f.event(2,60);assert.equal(f.hidden,1);
    f.window.minimized=true;f.event(1,40);f.event(3,200);f.terminal._firstFrame={};f.event(4,200,1,27);
    assert.equal(f.terminal._pendingShow,false);assert(f.balanced);
});
test('fullscreen swaps bulge for panel icon; overview and lock hide activators',()=>{
    const f=fixture();assert(f.handle.actor.visible);assert.equal(f.terminal._indicator.visible,false);
    f.fullscreen(true);assert.equal(f.handle.actor.visible,false);assert(f.terminal._indicator.visible);
    f.Main.overview.visible=true;f.handle.sync();assert.equal(f.terminal._indicator.visible,false);
    f.fullscreen(false);assert.equal(f.handle.actor.visible,false);
    f.Main.overview.visible=false;f.Main.sessionMode.isLocked=true;f.handle.sync();assert.equal(f.handle.actor.visible,false);
});
test('destroy releases active pointer grab',()=>{const f=fixture();f.event(1,40);f.event(3,200);f.handle.destroy();assert(f.balanced);});
