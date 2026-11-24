"""Preview Flatpak transactions without authorization, downloading or deployment."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from i18n import tr


def plan(scope, ref):
    import gi
    gi.require_version('Flatpak', '1.0')
    from gi.repository import Flatpak, GLib

    installation = (Flatpak.Installation.new_system(None) if scope == 'system'
                    else Flatpak.Installation.new_user(None))
    transaction = Flatpak.Transaction.new_for_installation(installation, None)
    transaction.set_no_interaction(True)
    transaction.add_default_dependency_sources()
    transaction.add_update(ref, None, None)
    operations = None

    def ready(tx):
        nonlocal operations
        operations = sorted((op.get_ref(), op.get_commit() or '') for op in tx.get_operations()
                            if not op.get_is_skipped())
        return False  # Abort before authentication or installation.

    transaction.connect('ready-pre-auth', ready)
    try:
        transaction.run(None)
    except GLib.Error:
        if operations is None:
            raise
    if operations is None:
        raise RuntimeError(tr('Flatpak could not verify the update plan.'))
    return operations


def failure_path(scope, ref):
    key = hashlib.sha256(f'{scope}:{ref}'.encode()).hexdigest()
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'infinityos/flatpak-updates' / key


def signature(operations, origin):
    return hashlib.sha256(json.dumps([origin, operations]).encode()).hexdigest()


def remember_failure(path, fingerprint, message):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False) as stream:
        json.dump({'plan': fingerprint, 'message': message[-2000:]}, stream)
    os.replace(stream.name, path)


def classify(scope, ref, version, origin):
    item = {'kind': 'Flatpak ' + scope, 'name': ref.split('/')[1],
            'version': version, 'source': origin, 'ref': ref}
    try:
        operations = plan(scope, ref)
    except Exception as error:
        return {**item, 'deferred': True, 'problem': str(error) or tr('Flatpak could not verify the update plan.')}
    if not operations:
        return None
    fingerprint = signature(operations, origin)
    item['plan'] = fingerprint
    try:
        failure = json.loads(failure_path(scope, ref).read_text())
    except (OSError, ValueError):
        failure = {}
    if isinstance(failure, dict) and failure.get('plan') == fingerprint:
        item.update(deferred=True, problem=failure.get('message') or tr('Flatpak installation failed.'), retryable=True)
    return item
