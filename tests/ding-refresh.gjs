// Run on Fedora with: gjs -m tests/ding-refresh.gjs /path/to/ding/app/desktopManager.js
import GLib from 'gi://GLib';

const {DesktopManager} = await import(GLib.filename_to_uri(ARGV[0], null));
const manager = Object.create(DesktopManager.prototype);
manager._readingDesktopFiles = false;
manager._desktopDir = {query_exists: () => true};
let reads = 0;
let draws = 0;
manager._doReadAsync = async () => {
    reads++;
    if (reads === 1)
        throw new Error('simulated persistent read failure');
    return [];
};
manager._drawDesktop = () => draws++;

try {
    await manager._updateDesktop();
    throw new Error('Expected the read failure to reach the caller');
} catch (e) {
    if (e.message !== 'simulated persistent read failure')
        throw e;
}
if (reads !== 1 || manager._readingDesktopFiles)
    throw new Error('Failed read left the desktop update busy');

await manager._updateDesktop();
if (reads !== 2 || draws !== 1 || manager._readingDesktopFiles)
    throw new Error('Desktop did not recover on the next update');
print('DING desktop refresh: error and recovery passed');
