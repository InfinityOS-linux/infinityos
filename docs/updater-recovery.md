# Update authorization and missing RPM recovery

If a client receives HTTP 404 for an older InfinityOS RPM after repository publication, refresh its repository metadata and check again:

```sh
sudo dnf clean metadata
sudo dnf --refresh makecache
```

Reopen InfinityUpdater, refresh the list, and select **Install updates**. These commands keep downloaded RPMs. They do not bypass signature checks or install packages directly into the running system.

Offline repository update preparation now retries a failed download once after `dnf clean metadata`. Local RPM installs and restart arming are not retried. The existing pending transaction metadata and restart trigger are restored if preparation fails.

The updater reports **Authorizing** while requesting administrator access. Polkit/PAM diagnostics are read separately from the authorized installer's JSON messages, so a warning cannot corrupt a successful authorization handshake. Authorization failures retain their diagnostic text, and unexpected worker exceptions finish with a visible error instead of leaving the update action busy. Shell modal interactions do not dismiss the updater drawer.

Regression coverage includes a real subprocess writing a diagnostic before its JSON ready message, cancellation and failure handling, bounded download retries, pending transaction preservation, progress phases, and Shell modal click/focus behavior. This does not establish the cause of an individual machine's transient transparent bar without its session logs.
