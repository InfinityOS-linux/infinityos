# InfinityTerminal keyboard editing at the Zsh prompt. Terminal output is
# handled by Ghostty; ZLE owns only the current command line.
# https://zsh.sourceforge.io/Doc/Release/Zsh-Line-Editor.html
[[ -o interactive && ${TERM:-} == xterm-ghostty ]] || return 0

# Keep the mascot even when an existing user has a personal Fastfetch config.
fastfetch() {
    command fastfetch --kitty-direct /usr/share/infinityos/ghostty/mascot.png \
        --logo-width 20 --logo-height 10 "$@"
}

_infinity_select() {
    if (( ! REGION_ACTIVE )); then
        MARK=$CURSOR
        REGION_ACTIVE=1
    fi
    case $WIDGET in
        infinity-select-left)       zle backward-char ;;
        infinity-select-right)      zle forward-char ;;
        infinity-select-up)         zle up-line ;;
        infinity-select-down)       zle down-line ;;
        infinity-select-word-left)  zle backward-word ;;
        infinity-select-word-right) zle forward-word ;;
    esac
}

for widget in infinity-select-{left,right,up,down,word-left,word-right}; do
    zle -N "$widget" _infinity_select
done
unset widget

_infinity_self_insert() {
    if (( REGION_ACTIVE && MARK != CURSOR )); then
        zle kill-region
    fi
    REGION_ACTIVE=0
    zle .self-insert
}

_infinity_backward_delete() {
    if (( REGION_ACTIVE && MARK != CURSOR )); then
        zle kill-region
    else
        zle .backward-delete-char
    fi
    REGION_ACTIVE=0
}

_infinity_delete() {
    if (( REGION_ACTIVE && MARK != CURSOR )); then
        zle kill-region
    else
        zle .delete-char
    fi
    REGION_ACTIVE=0
}

_infinity_bracketed_paste() {
    if (( REGION_ACTIVE && MARK != CURSOR )); then
        zle kill-region
    fi
    REGION_ACTIVE=0
    zle .bracketed-paste
}

# Alt+C copies the selected command text to the system clipboard using OSC 52.
# Ghostty 1.3.1 permits clipboard writes by default. Alt+W/Ctrl+Y remain the
# native Zsh copy/paste pair for the command line.
_infinity_copy_region() {
    (( REGION_ACTIVE && MARK != CURSOR )) || return 0
    local start end selected encoded
    if (( MARK < CURSOR )); then
        start=$MARK
        end=$CURSOR
    else
        start=$CURSOR
        end=$MARK
    fi
    selected=${BUFFER[$((start + 1)),$end]}
    encoded=$(print -rn -- "$selected" | base64 | tr -d '\r\n')
    zle copy-region-as-kill
    zle -I
    print -rn -- $'\e]52;c;'"$encoded"$'\a'
    zle redisplay
}

zle -N self-insert _infinity_self_insert
zle -N backward-delete-char _infinity_backward_delete
zle -N delete-char _infinity_delete
zle -N bracketed-paste _infinity_bracketed_paste
zle -N infinity-copy-region _infinity_copy_region

# Ghostty sends the standard xterm CSI sequences for modified arrow keys.
for keymap in emacs viins; do
    bindkey -M "$keymap" $'\e[1;2D' infinity-select-left
    bindkey -M "$keymap" $'\e[1;2C' infinity-select-right
    bindkey -M "$keymap" $'\e[1;2A' infinity-select-up
    bindkey -M "$keymap" $'\e[1;2B' infinity-select-down
    bindkey -M "$keymap" $'\e[1;6D' infinity-select-word-left
    bindkey -M "$keymap" $'\e[1;6C' infinity-select-word-right
    bindkey -M "$keymap" $'\e[1;3A' history-beginning-search-backward
    bindkey -M "$keymap" $'\e[1;3B' history-beginning-search-forward
    bindkey -M "$keymap" $'\x7f' backward-delete-char
    bindkey -M "$keymap" $'\x08' backward-delete-char
    bindkey -M "$keymap" $'\e[3~' delete-char
    bindkey -M "$keymap" $'\ec' infinity-copy-region
done
unset keymap
