import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as MonitorLayouts from '../root/usr/share/gnome-shell/extensions/ding@rastersoft.com/app/monitorLayouts.js';

const directory = '../root/usr/share/gnome-shell/extensions/ding@rastersoft.com/app/';
const Enums = {StoredCoordinates: {PRESERVE: 0, OVERWRITE: 1, ASSIGN: 2}};
const context = {
    MonitorLayouts, Enums,
    Prefs: {desktopSettings: {get_boolean: () => false}, getStartCorner: () => [false, false]},
    DesktopIconsUtil: {clamp: (value, low, high) => Math.min(high, Math.max(low, value))},
    imports: {gettext: {domain: () => ({gettext: text => text})}, signals: {addSignalMethods() {}}},
    Gio: {DesktopAppInfo: {new_from_filename: () => null},
        FileQueryInfoFlags: {NONE: 0},
        FileInfo: class {
            attributes = {};
            set_attribute_string(name, value) { this.attributes[name] = value; }
        }},
    desktopIconItem: {desktopIconItem: class {}},
    SignalManager: {SignalManager: class {}},
    Gtk: {Widget: class {}}, GObject: {registerClass() {}},
    print: text => { throw new Error(text); }, console,
};
function prototype(name, filename) {
    const source = readFileSync(new URL(directory + filename, import.meta.url), 'utf8')
        .replace(/^import .*;\n/gm, '').replace('export var ', 'var ');
    return vm.runInNewContext(`${source}\n${name}.prototype`, {...context});
}
const Manager = prototype('DesktopManager', 'desktopManager.js');
const File = prototype('FileItem', 'fileItem.js');
const Grid = prototype('DesktopGrid', 'desktopGrid.js');
const laptop = {x: 0, y: 0, width: 800, height: 600, scaleFactor: 1, monitorIndex: 0};
const external = {...laptop, x: 800, monitorIndex: 1};

function makeGrid(manager, area) {
    const grid = Object.create(Grid);
    Object.assign(grid, {
        _desktopManager: manager, _x: area.x, _y: area.y,
        _width: 800, _height: 600, _windowWidth: 800, _windowHeight: 600, _zoom: 1,
        _maxColumns: 8, _maxRows: 6, _elementWidth: 100, _elementHeight: 100,
        _gridStatus: Array(48).fill(false), _fileItems: {}, _container: {put() {}},
        _coordinatesBelongToThisGrid: (x, y) => x >= area.x && x < area.x + 800 &&
            y >= area.y && y < area.y + 600,
        coordinatesGlobalToLocal: (x, y) => [x - area.x, y - area.y],
        coordinatesLocalToGlobal: (x, y) => [x + area.x, y + area.y],
    });
    return grid;
}

function makeFile(manager, metadata) {
    const item = Object.create(File);
    Object.assign(item, {
        _desktopManager: manager, _savedCoordinates: metadata.legacy?.split(',').map(Number) ?? null,
        _monitorPositions: MonitorLayouts.readLayouts(metadata[MonitorLayouts.ATTRIBUTE]),
        _dropCoordinates: null, _fileExtra: 0,
        _file: {set_attributes_from_info(info) {
            metadata.writes = (metadata.writes ?? 0) + 1;
            Object.assign(metadata, info.attributes);
            metadata.legacy = metadata['metadata::nautilus-icon-position'];
        }},
        container: {},
        getCoordinates() { return [...this.actual]; },
        setCoordinates(x, y, width, height, spacing, grid) {
            this.actual = [x, y];
            this._grid = grid;
        },
    });
    Object.defineProperty(item, 'uri', {value: 'file:///Desktop/example'});
    return item;
}

function place(areas, metadata) {
    const manager = Object.create(Manager);
    manager._iconLayoutKey = MonitorLayouts.layoutKey(areas);
    manager._primaryScreen = areas[0];
    manager._desktops = areas.map(area => makeGrid(manager, area));
    const item = makeFile(manager, metadata);
    manager._fileList = [item];
    manager._placeAllFilesOnGrids();
    return item;
}

test('undocking keeps icons visible; reconnecting restores the external layout after edits and restart', () => {
    const metadata = {legacy: '1102,202'};
    assert.deepEqual(place([laptop, external], metadata).actual, [1102, 202]);
    const single = place([laptop], metadata);
    assert.ok(single.actual[0] >= 0 && single.actual[0] < laptop.width);
    assert.ok(single.actual[1] >= 0 && single.actual[1] < laptop.height);
    single.savedCoordinates = [102, 402];
    // Every place() creates new FileItems from serialized attributes, as after login.
    assert.deepEqual(place([laptop], metadata).actual, [102, 402]);
    assert.deepEqual(place([laptop, external], metadata).actual, [1102, 202]);
    assert.deepEqual(place([laptop], metadata).actual, [102, 402]);
});

test('unchanged desktop redraw does not rewrite position metadata', () => {
    const metadata = {legacy: '1102,202'};
    place([laptop, external], metadata);
    const writes = metadata.writes;
    place([laptop, external], metadata);
    assert.equal(metadata.writes, writes);
});

test('new icons and corrupt profile metadata use normal placement and establish a profile', () => {
    const metadata = {[MonitorLayouts.ATTRIBUTE]: '{broken'};
    const item = place([laptop], metadata);
    assert.deepEqual(item.actual, [2, 2]);
    assert.deepEqual(place([laptop], metadata).actual, [2, 2]);
});

test('monitor enumeration, primary selection and panel margins do not reset a layout', () => {
    const key = MonitorLayouts.layoutKey([laptop, external]);
    assert.equal(key, MonitorLayouts.layoutKey([
        {...external, monitorIndex: 0, primaryMonitor: 0, marginTop: 40},
        {...laptop, monitorIndex: 1, primaryMonitor: 0, marginBottom: 80},
    ]));
    assert.notEqual(key, MonitorLayouts.layoutKey([laptop, {...external, x: -800}]));
    assert.notEqual(key, MonitorLayouts.layoutKey([laptop, {...external, scaleFactor: 2}]));
    assert.notEqual(key, MonitorLayouts.layoutKey([laptop, {...external, y: -600}]));
    assert.equal(MonitorLayouts.layoutKey([]), null);
});

test('a negative-origin monitor restores independently of the laptop layout', () => {
    const left = {...external, x: -800};
    const metadata = {legacy: '-598,102'};
    assert.deepEqual(place([laptop, left], metadata).actual, [-598, 102]);
    assert.ok(place([laptop], metadata).actual[0] >= 0);
    assert.deepEqual(place([left, laptop], metadata).actual, [-598, 102]);
});

test('position resets affect only the active configuration; invalid history is ignored and bounded', () => {
    const dual = MonitorLayouts.layoutKey([laptop, external]);
    const single = MonitorLayouts.layoutKey([laptop]);
    let positions = MonitorLayouts.rememberPosition({}, dual, [1102, 202]);
    positions = MonitorLayouts.rememberPosition(positions, single, null);
    assert.equal(MonitorLayouts.positionForLayout(positions, single, [1, 2]), null);
    assert.deepEqual(MonitorLayouts.positionForLayout(positions, dual, null), [1102, 202]);
    assert.deepEqual(MonitorLayouts.readLayouts('{"v1:bad":["1",2]}'), {});
    for (let i = 0; i < 30; i++)
        positions = MonitorLayouts.rememberPosition(positions, `v1:${i}`, [i, i]);
    assert.equal(Object.keys(MonitorLayouts.readLayouts(JSON.stringify(positions))).length, 16);
});

test('nearest-screen fallback uses the vertical coordinate and skips full grids', () => {
    const grid = makeGrid({}, laptop);
    assert.equal(grid.getDistance(1000, 900), 600 ** 2 + 600 ** 2);
    grid._gridStatus.fill(true);
    assert.equal(grid.getDistance(1000, 900), -1);
});

test('changing only the primary monitor updates the new-file target without rebuilding icons', () => {
    const manager = Object.create(Manager);
    manager._desktopList = [laptop, external];
    manager._primaryIndex = 0;
    manager._primaryScreen = laptop;
    manager._createGridWindows = () => assert.fail('unchanged geometry should not recreate windows');
    manager.updateGridWindows([{...laptop, primaryMonitor: 1}, {...external, primaryMonitor: 1}]);
    assert.equal(manager._primaryScreen.x, external.x);
});
