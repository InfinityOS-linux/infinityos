// Return the files for the dock popup, or open an empty folder in the file manager.
export async function folderItemsOrOpen({ items, prepare, refresh, open }) {
  if (!items()) await prepare();
  let files = [...(items() || [])];
  if (!files.length && refresh) {
    await refresh();
    files = [...(items() || [])];
  }
  if (!files.length) {
    await open();
    return null;
  }
  return files;
}
