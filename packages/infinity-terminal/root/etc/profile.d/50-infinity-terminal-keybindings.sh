# Fedora sources profile.d scripts for interactive Zsh sessions. This also
# enables the bindings for users whose ~/.zshrc predates the new defaults.
if [ -n "${ZSH_VERSION:-}" ] && [ "${TERM:-}" = xterm-ghostty ]; then
    source /usr/share/infinityos/ghostty/keybindings.zsh
fi
