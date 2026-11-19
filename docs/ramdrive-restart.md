# RAMDrive restart choices

When RAMDrive contains files, GNOME's restart confirmation appears in the upper-right corner with two actions:

- **Remove & Restart** removes the current user's RAMDrive contents, then resumes GNOME's normal restart confirmation.
- **Save files** moves the contents to **Saved Files** on the user's configured Desktop, then resumes the restart.

Existing saved files are retained. Colliding names receive numeric suffixes; hidden files, nested directories, and symbolic links are included. The protected RAMDrive folder and desktop shortcut remain in place. A failed operation or remaining files stops confirmation and displays an error. The normal countdown cannot restart the machine while a choice is pending. Escape cancels before an operation starts; disabling the extension or closing the request during an operation prevents its completion callback from restarting the machine.

The dialog retains GNOME's update checkbox, application inhibitors, and other-session information. Empty RAMDrive, logout, and power-off confirmations retain their existing behavior. The session guard remains as a fallback when desktop extensions are disabled. These choices apply to normal GNOME restart requests, not a forced reset or commands that bypass the desktop session.

The file operation runs as the current user. Saved Files must be outside RAMDrive and cannot be a symbolic link. On partial failure, already moved files stay in Saved Files and remaining files stay in RAMDrive; no restart is confirmed.

Validation covers filesystem moves and failures in temporary directories, restart ordering and teardown in JavaScript tests, and the real GNOME 51 dialog in the disposable Shell smoke session. Native tests replace the final reboot callback and file operation so they never reboot the runner or touch user files.
