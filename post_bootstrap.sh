#!/bin/sh
set -eu

case ",${kiwi_profiles:-}," in
    *,Infinity-GNOME-Live,*|*,Infinity-GNOME-Disk,*) ;;
    *) exit 0 ;;
esac

# Fedora 45 DNF5 otherwise fails on Workstation group members we deliberately exclude.
test -f /kiwi_dnf5.config
printf 'skip_unavailable = true\n' >> /kiwi_dnf5.config
