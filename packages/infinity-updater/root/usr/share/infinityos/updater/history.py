"""Private, bounded operation history shared by updater windows."""
import fcntl
from datetime import datetime, timezone
from checker import state_path, read_state, save_state


def read_history():
    value = read_state(state_path().parent / 'history.json')
    return value if isinstance(value, list) else []


def record_operation(source, status, detail=''):
    directory = state_path().parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / 'history.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = read_history()
        entries.insert(0, {'time': datetime.now(timezone.utc).isoformat(),
                          'source': source, 'status': status, 'detail': detail[:2000]})
        save_state(entries[:100], directory / 'history.json')
