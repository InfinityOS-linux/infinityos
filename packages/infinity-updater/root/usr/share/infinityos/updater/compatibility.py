"""Read-only RPM solver inspection; never download or run a transaction."""
import os
from pathlib import Path
import tempfile

from pending import package_key


def classify_transaction(updates, transaction):
    """Only mark exact candidates explicitly skipped by the dependency solver."""
    blocked = {}
    for reason, packages in (('dependencies', transaction.get_broken_dependency_packages()),
                             ('conflict', transaction.get_conflicting_packages())):
        for package in packages:
            blocked[(package.get_name(), package.get_arch(),
                     package.get_evr().removeprefix('0:'))] = reason
    result = []
    for item in updates:
        clean = {key: value for key, value in item.items()
                 if key not in ('deferred', 'deferred_reason')}
        reason = blocked.get(package_key(item)) if item['kind'] == 'RPM' else None
        result.append({**clean, 'deferred': True, 'deferred_reason': reason} if reason else clean)
    return result


def resolve(base, libdnf5):
    goal = libdnf5.base.Goal(base)
    goal.add_rpm_upgrade()
    transaction = goal.resolve()
    if transaction.get_problems() != libdnf5.base.GoalProblem_NO_PROBLEM:
        raise RuntimeError('; '.join(transaction.get_resolve_logs_as_strings()))
    return transaction


def classify_updates(updates):
    if not any(item['kind'] == 'RPM' for item in updates):
        return updates
    try:
        import libdnf5
        import libdnf5.base
    except ImportError:
        # Older installations can still check before the bindings are installed.
        # Missing solver information is not evidence of a compatibility hold.
        return updates
    with tempfile.TemporaryDirectory(prefix='infinityos-rpm-solver-') as state_dir:
        base = libdnf5.base.Base()
        base.load_config()
        config = base.get_config()
        config.system_state_dir = state_dir
        config.cachedir = str(Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'libdnf5')
        config.best = False  # Match the installer's --no-best policy.
        config.skip_unavailable = True
        config.assumeyes = True  # Repository keys only; no transaction is executed.
        base.setup()
        sack = base.get_repo_sack()
        sack.create_repos_from_system_configuration()
        sack.load_repos()
        transaction = resolve(base, libdnf5)
        return classify_transaction(updates, transaction)
