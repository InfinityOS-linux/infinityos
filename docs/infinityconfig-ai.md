# AI in InfinityConfig

The AI tab follows InfinitySetup's selection. Provider CLIs must have both the
user-prefix executable and the desktop entry created by Setup. Local AI uses
`~/.config/infinityos/local-ai-model`. Config checks for changes every two seconds;
removing the last selection hides the tab and returns to Desktop.

Account controls use the provider CLI, without reading or storing credentials.
Login opens Infinity Terminal; Refresh retrieves the resulting account status.
Logout asks for confirmation. Model selection for hosted providers opens their
terminal, where `/model` lists the models available to that account.

Codex uses the documented app-server account, rate-limit and usage endpoints.
Quota percentages are remaining portions of the provider's time windows, not
invented token balances. Older clients can omit usage data. Claude exposes auth
status through its CLI; its usage link opens the provider's account page because
there is no documented equivalent quota endpoint in its CLI.

Local models are listed by Ollama. Apply creates a per-user Ollama alias with the
chosen context, response limit and temperature, then selects it for new Infinity
AI sessions. GGUF import adds a model to the list; Apply selects it. Existing
sessions retain their model. Setup also lists a custom selection so it can be
turned off without deleting downloaded weights.

Storage changes copy **all** Ollama models to an empty folder owned by the desktop
user and accessible to the `ollama` service account. A folder on a mounted data
disk is suitable; a private home directory may block service access. Administrator
authentication is required. The service stops during the copy. The original files
are retained; a failed switch restores the previous service override. This action
supports the standard system service running as `ollama`, not custom user services.
The selected folder is shared with the Ollama service group.

All new controls have English and Polish text selected by the system locale.

## Verification

Run `xvfb-run -a dbus-run-session -- scripts/test-infinity-delta source` in Fedora
with GTK4 and PyGObject installed. Tests use simulated provider replies, temporary
model selections and mocked service operations; they do not log out real accounts,
download weights or move the host's model directory.

Protocol references:
- https://developers.openai.com/codex/app-server
- https://code.claude.com/docs/en/cli-reference
- https://docs.ollama.com/api/create
- https://docs.ollama.com/faq
