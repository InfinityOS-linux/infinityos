// Run on Fedora with: gjs -m tests/ding-thumbnails.gjs /path/to/ding/app/thumbnails.js
import GLib from 'gi://GLib';

const {ThumbnailLoader} = await import(GLib.filename_to_uri(ARGV[0], null));

function newLoader(failedThumbnail = false) {
    const loader = Object.create(ThumbnailLoader.prototype);
    loader._thumbList = [];
    loader._running = false;
    loader._thumbnailFactoryLarge = {
        has_valid_failed_thumbnail: () => failedThumbnail,
    };
    loader._resolveThumbnail = () => false;
    loader._createThumbnailAsync = (_file, resolve) => {
        resolve('next');
        loader._launchNewBuild();
    };
    loader._useAsyncAPI = true;
    return loader;
}

async function expectSettled(loader, file, expected) {
    const result = await Promise.race([
        new Promise(resolve => {
            loader._thumbList.push([file, resolve]);
            loader._launchNewBuild();
        }),
        new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
            resolve('timeout');
            return GLib.SOURCE_REMOVE;
        })),
    ]);
    if (result !== expected)
        throw new Error(`Expected ${expected}, got ${result}`);
    if (loader._running)
        throw new Error('Thumbnail queue stayed busy');
}

await expectSettled(newLoader(), {_destroyed: true}, null);
await expectSettled(newLoader(), {_destroyed: false, file: {query_exists: () => false}}, null);
await expectSettled(newLoader(true), {
    _destroyed: false,
    file: {query_exists: () => true},
    uri: 'file:///tmp/failed-thumbnail',
    modifiedTime: 1,
}, null);
await expectSettled(newLoader(), {
    _destroyed: false,
    file: {query_exists: () => true},
}, 'next');

const throwingLoader = newLoader();
throwingLoader._thumbnailFactoryLarge.generate_thumbnail_async = () => {
    throw new Error('simulated thumbnail backend failure');
};
throwingLoader._createThumbnailAsync = ThumbnailLoader.prototype._createThumbnailAsync;
throwingLoader._createFailedThumbnailAsync = (_file, _time, resolve) => {
    resolve(null);
    throwingLoader._launchNewBuild();
};
await expectSettled(throwingLoader, {
    _destroyed: false,
    file: {
        query_exists: () => true,
        query_info: () => ({
            get_attribute_uint64: () => 1,
            get_content_type: () => 'image/png',
        }),
    },
    uri: 'file:///tmp/thumbnail-backend-error',
}, null);

const racingLoader = newLoader();
racingLoader._timeoutValue = 10;
let generationCallback;
let fallbackCalls = 0;
let nextTimeoutFired = false;
racingLoader._thumbnailFactoryLarge.generate_thumbnail_async = (_uri, _type, _cancel, callback) => {
    generationCallback = callback;
};
racingLoader._createThumbnailAsync = ThumbnailLoader.prototype._createThumbnailAsync;
racingLoader._createFailedThumbnailAsync = (_file, _time, resolve) => {
    fallbackCalls++;
    resolve(null);
};
const timedOut = new Promise(resolve => racingLoader._createThumbnailAsync({
    file: {query_info: () => ({
        get_attribute_uint64: () => 1,
        get_content_type: () => 'image/png',
    })},
    uri: 'file:///tmp/thumbnail-race',
    displayName: 'thumbnail-race',
}, resolve));
if (await timedOut !== null)
    throw new Error('Timeout did not settle the thumbnail');
racingLoader._timeoutID = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 10, () => {
    nextTimeoutFired = true;
    return GLib.SOURCE_REMOVE;
});
generationCallback({generate_thumbnail_finish: () => {
    throw new Error('cancelled generation');
}}, null);
await new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, 30, () => {
    resolve();
    return GLib.SOURCE_REMOVE;
}));
if (fallbackCalls !== 1 || !nextTimeoutFired)
    throw new Error('Late callback interfered with the next thumbnail');

print('DING thumbnail queue: 6 cases passed');
