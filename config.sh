#!/bin/bash

set -euxo pipefail

#======================================
# Functions...
#--------------------------------------
test -f /.kconfig && . /.kconfig
test -f /.profile && . /.profile

#======================================
# Greeting...
#--------------------------------------
echo "Configure image: [$kiwi_iname]-[$kiwi_profiles]..."

# Apply Infinity OS defaults only to its GNOME image profiles.
if [[ "$kiwi_profiles" == *"Infinity-GNOME"* ]]; then
	# Reject an old RPM repository or a reused prepared root before making an image.
	# The supported kiwi-build wrapper stages a clean commit and its revision.
	build_revision=$(cat /usr/share/infinityos/build-revision)
	/usr/libexec/infinityos-verify-build-root / "$build_revision"
	/usr/libexec/infinityos-style-gdm
	# Hide GNOME's blue Adwaita default from the wallpaper chooser.
	rm -f /usr/share/gnome-background-properties/adwaita.xml
	release_version=$(cat /usr/share/infinityos/image-release-version)
	[[ $release_version =~ ^[1-9][0-9]*\.[0-9]+(\.[0-9]+)?$ ]] || exit 1
	rm -f /etc/os-release
	cat > /etc/os-release << EOF
NAME="Infinity OS"
PRETTY_NAME="Infinity OS ${release_version} (Fedora 44)"
ID=infinityos
ID_LIKE=fedora
VERSION_ID=44
VERSION="44"
INFINITYOS_VERSION_ID=${release_version}
VARIANT="GNOME Workstation"
VARIANT_ID=workstation
LOGO=infinityos-logo
ANSI_COLOR="0;38;2;100;83;148"
HOME_URL="https://github.com/InfinityOS-linux/infinityos"
DOCUMENTATION_URL="https://github.com/InfinityOS-linux/infinityos/blob/main/README.md"
EOF
	printf '%s\n' "$release_version" > /etc/infinityos-release
	printf 'Infinity OS %s (Fedora 44)\n' "$release_version" > /etc/issue
	printf 'Infinity OS %s (Fedora 44)\n' "$release_version" > /etc/issue.net
	chmod 0644 /etc/os-release /etc/infinityos-release /etc/issue /etc/issue.net
	if rpm -q mediawriter >/dev/null 2>&1; then
		dnf -y remove mediawriter
	fi
	if command -v plymouth-set-default-theme >/dev/null; then
		for image in bullet capslock entry keyboard keymap-render lock; do
			cp -f "/usr/share/plymouth/themes/spinner/$image.png" /usr/share/plymouth/themes/infinityos/
		done
		plymouth-set-default-theme infinityos
	fi
	install -d /usr/share/icons /usr/share/licenses/kora
	tar -xzf /usr/share/infinityos/kora-v2.0.6.tar.gz -C /usr/share/icons --strip-components=1 kora-2.0.6/kora/
	cp -a /usr/share/infinityos/folder-icons/. /usr/share/icons/kora/places/scalable/
	rm -f /usr/share/icons/kora/apps/scalable/org.gnome.Nautilus.svg
	install -m 0644 /usr/share/infinityos/folder-icons/folder.svg /usr/share/icons/kora/apps/scalable/org.gnome.Nautilus.svg
	cp -f /usr/share/icons/hicolor/256x256/apps/infinityos-logo.png /usr/share/cockpit/branding/infinityos/logo.png
	cp -f /usr/share/backgrounds/infinityos/infinityos-dark.png /usr/share/cockpit/branding/infinityos/wallpaper.png
	tar -xOf /usr/share/infinityos/kora-v2.0.6.tar.gz kora-2.0.6/LICENSE > /usr/share/licenses/kora/LICENSE
	rm /usr/share/infinityos/kora-v2.0.6.tar.gz
	gtk-update-icon-cache -f -q /usr/share/icons/kora
	# The welcome screen resolves this icon through GTK's hicolor cache.
	# The source overlay installs it after Fedora generated the original cache.
	gtk-update-icon-cache -f -q /usr/share/icons/hicolor
	tar -xf /usr/share/infinityos/Bibata-Modern-Ice-v2.0.7.tar.xz -C /usr/share/icons
	rm /usr/share/infinityos/Bibata-Modern-Ice-v2.0.7.tar.xz
	glib-compile-schemas /usr/share/gnome-shell/extensions/ding@rastersoft.com/schemas
	glib-compile-schemas /usr/share/gnome-shell/extensions/wack-lockscreen-clock@rinzler69-wastaken.github.com/schemas
	glib-compile-schemas /usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/schemas
	glib-compile-schemas /usr/share/gnome-shell/extensions/tilingshell@ferrarodomenico.com/schemas
	glib-compile-schemas /usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/schemas
	chmod 0644 \
		/usr/share/gnome-shell/extensions/ding@rastersoft.com/schemas/gschemas.compiled \
		/usr/share/gnome-shell/extensions/wack-lockscreen-clock@rinzler69-wastaken.github.com/schemas/gschemas.compiled \
		/usr/share/gnome-shell/extensions/wack-shell@rinzler69-wastaken.github.com/schemas/gschemas.compiled
	chmod 0644 /usr/share/gnome-shell/extensions/tilingshell@ferrarodomenico.com/schemas/gschemas.compiled
	chmod 0644 /usr/share/gnome-shell/extensions/dash2dock-animated@infinityos.org/schemas/gschemas.compiled
	install -d /etc/skel/Desktop /etc/environment.d
	printf 'XCURSOR_THEME=Bibata-Modern-Ice\n' > /etc/environment.d/90-infinityos-cursor.conf
	# Image overlays can make Oh My Zsh directories group-writable, which disables completions.
	chmod -R go-w /usr/share/oh-my-zsh
	/usr/libexec/infinityos-install-iosevka
	GITSTATUS_CACHE_DIR=/usr/share/oh-my-zsh/custom/themes/powerlevel10k/gitstatus/usrbin \
		/usr/share/oh-my-zsh/custom/themes/powerlevel10k/gitstatus/install
	chmod 0755 /usr/share/oh-my-zsh/custom/themes/powerlevel10k/gitstatus/usrbin
	install -m 0644 /usr/share/infinityos/zshrc /etc/skel/.zshrc
	fc-cache -f
	install -d /etc/skel/.config/gtk-4.0
	ln -sfn /usr/share/infinityos/gtk4-adaptive.css /etc/skel/.config/gtk-4.0/gtk.css
	install -d /etc/dconf/db/local.d
	ln -sfn /usr/share/infinityos/gnome-defaults /etc/dconf/db/local.d/00-infinityos
	ln -sfn /usr/share/infinityos/blur-defaults /etc/dconf/db/local.d/01-infinity-blur
	install -D -m 0644 /usr/share/infinityos/repos/docker-ce.repo /etc/yum.repos.d/docker-ce.repo
	install -D -m 0644 /usr/share/infinityos/repos/rounded-blur.repo /etc/yum.repos.d/rounded-blur.repo
	install -D -m 0644 /usr/share/infinityos/mimeapps.list /etc/xdg/mimeapps.list
	/usr/libexec/infinityos-install-proview
	# systemd applies vendor presets on the first boot of an image with an
	# uninitialized machine-id. Preserve the services enabled below.
	cat > /usr/lib/systemd/system-preset/00-infinityos.preset << 'EOF'
enable systemd-resolved.service
enable tlp.service
enable tlp-pd.service
enable infinityos-ramdrive.service
enable infinityos-ramdrive-prepare.path
enable infinityos-ramdrive-prepare.service
enable infinityos-corefonts.timer
enable infinityos-repo-trust.timer
disable infinityos-corefonts.service
disable infinityos-repo-trust.service
EOF
	install -d /etc/gnome-initial-setup
	cat > /etc/gnome-initial-setup/vendor.conf << 'EOF'
[pages]
existing_user_only=language;keyboard
skip=software;privacy
EOF
	fedora-third-party enable
	# Install performance policy only in Infinity OS images. The shared KIWI
	# source tree also builds upstream Fedora profiles.
	install -D -m 0644 /usr/share/infinityos/performance/zram-generator.conf /etc/systemd/zram-generator.conf
	install -D -m 0644 /usr/share/infinityos/performance/75-infinityos-network.conf /etc/sysctl.d/75-infinityos-network.conf
	install -D -m 0644 /usr/share/infinityos/performance/80-infinityos-inotify.conf /etc/sysctl.d/80-infinityos-inotify.conf
	install -D -m 0644 /usr/share/infinityos/performance/60-infinityos-ioschedulers.rules /etc/udev/rules.d/60-infinityos-ioschedulers.rules
	systemctl disable infinityos-corefonts.service infinityos-repo-trust.service
	systemctl enable systemd-resolved.service tlp.service tlp-pd.service switcheroo-control.service infinityos-ramdrive.service infinityos-ramdrive-prepare.path infinityos-ramdrive-prepare.service infinityos-corefonts.timer infinityos-repo-trust.timer
	printf 'user-db:user\nsystem-db:local\n' > /etc/dconf/profile/user
	dconf update
	# GPaste's Shell indicator activates its daemon over D-Bus after login.
	# Avoid starting it before the user session or for accounts without the indicator.
	printf 'disable org.gnome.GPaste.service\n' > /usr/lib/systemd/user-preset/00-infinityos.preset
	systemctl --global disable org.gnome.GPaste.service
	# KIWI runs with a restrictive umask; the initial-setup account must read
	# this compiled database to get the Infinity OS wallpaper and dark theme.
	chmod 0644 /etc/dconf/db/infinityos-initial-setup /etc/dconf/db/gdm /etc/dconf/db/local
	# Fedora 44's greeter entry starts the default user session on this image.
	# That renders a desktop without the login form. Select the GNOME login
	# session explicitly until the packaged desktop entry does so itself.
	greeter=/usr/share/gdm/greeter/wayland-sessions/gnome-greeter.desktop
	if [[ -f "$greeter" ]]; then
		sed -i 's/^Exec=gnome-session$/Exec=gnome-session --session=gnome-login/' "$greeter"
		grep -qx 'Exec=gnome-session --session=gnome-login' "$greeter"
	fi
	useradd -D -s /usr/bin/zsh
	if id liveuser &>/dev/null; then
		usermod -s /usr/bin/zsh liveuser
		install -d -o liveuser -g liveuser /home/liveuser/Desktop
		install -m 0644 /usr/share/infinityos/zshrc /home/liveuser/.zshrc
		chown liveuser:liveuser /home/liveuser/.zshrc
		install -d -o liveuser -g liveuser /home/liveuser/.config/gtk-4.0
		ln -sfn /usr/share/infinityos/gtk4-adaptive.css /home/liveuser/.config/gtk-4.0/gtk.css
	fi
	if [[ "$kiwi_profiles" == *"Infinity-GNOME-Live"* ]]; then
		# This profile uses GRUB only while KIWI composes the ISO. The
		# unrelated systemd-boot package is not needed in the live root.
		if rpm -q systemd-boot-unsigned >/dev/null 2>&1; then
			rpm -e systemd-boot-unsigned
		fi
		# livesys creates liveuser on first boot and copies /etc/skel then.
		# Keep GNOME running while Anaconda is open; the dock hides for its window.
		installer_desktop=/usr/share/applications/liveinst.desktop
		test -f "$installer_desktop"
		grep -qx 'Exec=liveinst' "$installer_desktop"
		grep -q '^Icon=' "$installer_desktop"
		sed -i 's/^Icon=.*/Icon=infinity-installer/' "$installer_desktop"
		grep -qx 'Icon=infinity-installer' "$installer_desktop"
		install -d /etc/skel/.config/autostart
		cat > /etc/skel/.config/autostart/infinityos-live-power.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Infinity OS live session power settings
Exec=/usr/libexec/infinityos-live-power
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF
		# Apply live-session defaults before GNOME starts. Keep the terminal
		# controller inactive while Anaconda runs; installed accounts use local.
		# Autostart remains a fallback for stale liveuser power settings.
		install -d /etc/dconf/db/infinityos-live.d
		cat > /etc/dconf/db/infinityos-live.d/00-power << 'EOF'
[org/gnome/shell]
disabled-extensions=['ghostty@infinityos.org']

[org/gnome/desktop/session]
idle-delay=uint32 0

[org/gnome/desktop/screensaver]
idle-activation-enabled=false
lock-enabled=false

[org/gnome/settings-daemon/plugins/power]
idle-dim=false
sleep-inactive-ac-type='nothing'
sleep-inactive-battery-type='nothing'
EOF
		printf 'user-db:user\nsystem-db:infinityos-live\nsystem-db:local\n' > /etc/dconf/profile/user
		dconf update
		chmod 0644 /etc/dconf/db/infinityos-live
	fi
	if [[ "$kiwi_profiles" == *"Infinity-GNOME-Disk"* ]]; then
		# The build host's storage controller differs from the target VM or PC.
		printf 'hostonly="no"\n' > /etc/dracut.conf.d/99-infinityos-generic.conf
		systemctl enable infinityos-snapper-setup.service infinityos-backups-setup.service infinityos-backups-entry.service infinityos-backups-entry.path snapper-timeline.timer snapper-cleanup.timer
		cat >> /usr/lib/systemd/system-preset/00-infinityos.preset << 'EOF'
enable infinityos-snapper-setup.service
enable infinityos-backups-setup.service
enable infinityos-backups-entry.service
enable infinityos-backups-entry.path
enable snapper-timeline.timer
enable snapper-cleanup.timer
EOF
	fi
	if [[ "$kiwi_profiles" == *"Infinity-GNOME-Live"* ]]; then
		# Anaconda WebUI builds its localized title from PRETTY_NAME.
		# Keep the installed system's release name; the post-install hook restores it.
		installer_name="InfinityOS_${release_version}"
		[[ $release_version == 1.0 ]] && installer_name=InfinityOS_01
		sed -i "s/^PRETTY_NAME=.*/PRETTY_NAME=\"$installer_name\"/" /etc/os-release
		grep -Fqx "PRETTY_NAME=\"$installer_name\"" /etc/os-release
		if [[ "$(uname -m)" == x86_64 || "$(uname -m)" == aarch64 ]]; then
			# Anaconda copies the live root to the target. Keep a pending marker
			# until the post script finishes; the retry unit needs both this marker
			# and a mounted target ESP before it can run.
			install -d /etc/infinityos
			touch /etc/infinityos/liveinstall-boot-pending
			systemctl enable infinityos-liveinstall-boot-setup.service
			case $(uname -m) in
				x86_64) rpm -q rEFInd rEFInd-unsigned-x64 snapper efibootmgr ;;
				aarch64) rpm -q rEFInd rEFInd-unsigned-aa64 snapper efibootmgr ;;
			esac
			cat >> /usr/lib/systemd/system-preset/00-infinityos.preset << 'EOF'
enable infinityos-liveinstall-boot-setup.service
EOF
		fi
		# Anaconda selects its profile from os-release. With ID=infinityos it
		# otherwise falls back to EFI/default, where the packaged shim is absent.
		test -f /etc/anaconda/profile.d/infinityos.conf
		chmod 0644 /etc/anaconda/profile.d/infinityos.conf
		cat > /.buildstamp << 'EOF'
[Main]
Product=Infinity OS
Version=44
IsFinal=True
EOF
		chmod 0644 /.buildstamp
		welcome=/usr/share/anaconda/gnome/fedora-welcome
		welcome_desktop=/usr/share/anaconda/gnome/org.fedoraproject.welcome-screen.desktop
		test -f "$welcome" && test -f "$welcome_desktop"
		grep -Eq "iconName: '(fedora-logo-icon|infinityos-logo|infinity-installer)'" "$welcome"
		sed -i -e "s/iconName: 'fedora-logo-icon'/iconName: 'infinity-installer'/" \
			-e "s/iconName: 'infinityos-logo'/iconName: 'infinity-installer'/" "$welcome"
		grep -Fq "iconName: 'infinity-installer'" "$welcome"
		sed -i -e 's/^Name=Welcome to Fedora$/Name=Welcome to Infinity OS/' \
			-e 's/^Icon=fedora-logo-icon$/Icon=infinityos-logo/' \
			-e '/^Name\[/d' "$welcome_desktop"
		# Live media mounts its root dynamically; disk-image UUIDs must not reach the ISO.
		: > /etc/fstab
		# Anaconda must create an ESP and kernel metadata. The post script
		# replaces its EFI loader with rEFInd before reporting success.
		if [[ "$(uname -m)" == x86_64 || "$(uname -m)" == aarch64 ]]; then
			# Keep Anaconda's UEFI bootloader enabled while it partitions the
			# destination. Disabling it also suppresses the required ESP. The
			# post script replaces its EFI loader with rEFInd before success.
			# Fedora's gen_grub_cfgstub assumes the EFI vendor directory already
			# exists. Its package creates EFI/fedora, but our Anaconda profile uses
			# EFI/infinityos. Create that directory in the installer target.
			cfgstub=/usr/sbin/gen_grub_cfgstub
			test -f "$cfgstub"
			if ! grep -Fqx 'mkdir -p "$EFI_HOME"' "$cfgstub"; then
				grep -Fqx 'EFI_HOME=$2' "$cfgstub"
				sed -i '/^EFI_HOME=\$2$/a mkdir -p "$EFI_HOME"' "$cfgstub"
			fi
			# Anaconda 44 parses interactive-defaults.ks for liveinst, but no
			# longer calls appendPostScripts(). Put required hooks in the file it
			# actually reads so success requires a working rEFInd install.
			cat >> /usr/share/anaconda/interactive-defaults.ks <<'BOOT_POST_EOF'
%post --erroronfail --log=/var/log/infinityos-boot-install.log
/usr/libexec/infinityos-liveinstall-boot-setup
%end
BOOT_POST_EOF
		fi
		# PatternFly's dark token set is selected on the document root.
		sed -i 's/<html lang="en">/<html lang="en" class="pf-v6-theme-dark">/' /usr/share/cockpit/anaconda-webui/index.html
		grep -q '</head>' /usr/share/cockpit/anaconda-webui/index.html
		if ! grep -q 'infinityos-font.css' /usr/share/cockpit/anaconda-webui/index.html; then
			sed -i 's@</head>@<link rel="stylesheet" href="infinityos-font.css"></head>@' \
				/usr/share/cockpit/anaconda-webui/index.html
		fi
		/usr/bin/python3 /usr/libexec/infinityos-brand-installer
		# Anaconda opens its own temporary Firefox profile. Allow the installer
		# music to begin when that window opens, before the first page click.
		firefox_live_prefs=/usr/share/anaconda/firefox-theme/live/user.js
		test -f "$firefox_live_prefs"
		if ! grep -Fq 'user_pref("media.autoplay.default", 0);' "$firefox_live_prefs"; then
			printf '%s\n' 'user_pref("media.autoplay.default", 0);' >> "$firefox_live_prefs"
		fi
		# Fedora hides Firefox chrome for Anaconda. Use the native window title
		# bar so the installer can be moved by dragging it.
		webui_desktop=/usr/libexec/anaconda/webui-desktop
		grep -Fq 'MOZ_GTK_TITLEBAR_DECORATION=client' "$webui_desktop"
		sed -i 's/MOZ_GTK_TITLEBAR_DECORATION=client/MOZ_GTK_TITLEBAR_DECORATION=system/' "$webui_desktop"
		if ! grep -Fq 'user_pref("browser.tabs.inTitlebar", 0);' "$firefox_live_prefs"; then
			printf '%s\n' 'user_pref("browser.tabs.inTitlebar", 0);' >> "$firefox_live_prefs"
		fi
		if [[ "$(uname -m)" == "x86_64" ]]; then
			# Detect the target PC while Anaconda still has access to its PCI devices.
			# A failed network download is retried after installation at boot.
			cat >> /usr/share/anaconda/interactive-defaults.ks <<'NVIDIA_POST_EOF'
%post --nochroot --log=/mnt/sysroot/var/log/infinityos-nvidia-install.log
if ! /usr/libexec/infinityos-install-nvidia /mnt/sysroot; then
    mkdir -p /mnt/sysroot/etc/systemd/system/multi-user.target.wants
    ln -sfn /usr/lib/systemd/system/infinityos-nvidia-retry.service /mnt/sysroot/etc/systemd/system/multi-user.target.wants/infinityos-nvidia-retry.service
fi
%end
NVIDIA_POST_EOF
		fi
	fi
fi

#======================================
# Set SELinux booleans
#--------------------------------------
if [[ "$kiwi_profiles" != *"Container"* ]] && [[ "$kiwi_profiles" != *"FEX"* ]] && [[ "$kiwi_profiles" != *"WSL"* ]]; then
	## Fixes KDE Plasma, see rhbz#2058657
	setsebool -P selinuxuser_execmod 1
fi

#======================================
# Clear machine specific configuration
#--------------------------------------
## Clear machine-id on pre generated images
rm -f /etc/machine-id
echo 'uninitialized' > /etc/machine-id
chmod 0644 /etc/machine-id
## remove random seed, the newly installed instance should make its own
rm -f /var/lib/systemd/random-seed

#======================================
# Configure grub correctly
#--------------------------------------
if [[ "$kiwi_profiles" != *"Container"* ]] && [[ "$kiwi_profiles" != *"FEX"* ]] && [[ "$kiwi_profiles" != *"WSL"* ]] && [[ "$kiwi_profiles" != *"Infinity-GNOME-"* ]]; then
	## Works around issues with grub-bls
	## See: https://github.com/OSInside/kiwi/issues/2198
	echo "GRUB_DEFAULT=saved" >> /etc/default/grub
	## Disable submenus to match Fedora
	echo "GRUB_DISABLE_SUBMENU=true" >> /etc/default/grub
	## Disable recovery entries to match Fedora
	echo "GRUB_DISABLE_RECOVERY=true" >> /etc/default/grub
	if [[ "$kiwi_profiles" == *"Disk"* ]]; then
		## Write `menu_auto_hide=1` into grubenv to match Fedora anaconda installs
		## Set boot_indeterminate to avoid displaying the grub menu on first boot
		if [[ "$kiwi_profiles" != *"Server"* ]] || [[ "$kiwi_profiles" != *"Cloud"* ]]; then
			grub2-editenv /boot/grub2/grubenv set menu_auto_hide=1 boot_indeterminate=1
		fi
	fi
fi

#======================================
# Resize root partition on first boot
#--------------------------------------

if [[ "$kiwi_profiles" == *"Disk"* ]]; then
	mkdir -p /etc/repart.d/
	cat > /etc/repart.d/50-root.conf << EOF
[Partition]
Type=root
EOF
fi

#======================================
# Delete & lock the root user password
#--------------------------------------
if [[ "$kiwi_profiles" == *"Cloud"* ]] || [[ "$kiwi_profiles" == *"Disk"* ]] || [[ "$kiwi_profiles" == *"Live"* ]] || [[ "$kiwi_profiles" == *"WSL"* ]]; then
	passwd -d root
	passwd -l root
fi

#======================================
# Setup default services
#--------------------------------------

if [[ "$kiwi_profiles" == *"Live"* ]]; then
	## Configure livesys session
	if [[ "$kiwi_profiles" == *"Infinity-GNOME-Live"* ]]; then
		systemctl enable livesys.service livesys-late.service
		cat >> /usr/lib/systemd/system-preset/00-infinityos.preset << 'EOF'
enable livesys.service
enable livesys-late.service
EOF
	fi
	if [[ "$kiwi_profiles" == *"GNOME"* ]]; then
		echo 'livesys_session="gnome"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"KDE"* ]]; then
		echo 'livesys_session="kde"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"Budgie"* ]]; then
		echo 'livesys_session="budgie"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"Cinnamon"* ]]; then
		echo 'livesys_session="cinnamon"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"COSMIC"* ]]; then
		echo 'livesys_session="cosmic"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"i3"* ]]; then
		echo 'livesys_session="i3"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"LXDE"* ]]; then
		echo 'livesys_session="lxde"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"LXQt"* ]]; then
		echo 'livesys_session="lxqt"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"MATE_Compiz"* ]]; then
		echo 'livesys_session="mate"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"MiracleWM"* ]]; then
		echo 'livesys_session="miraclewm"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"Sway"* ]]; then
		echo 'livesys_session="sway"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"SoaS"* ]]; then
		echo 'livesys_session="soas"' > /etc/sysconfig/livesys
	fi
	if [[ "$kiwi_profiles" == *"Xfce"* ]]; then
		echo 'livesys_session="xfce"' > /etc/sysconfig/livesys
	fi
fi

#======================================
# Setup firstboot initial setup
#--------------------------------------

if [[ "$kiwi_profiles" == *"Disk"* ]]; then
	if [[ "$kiwi_profiles" != *"GNOME"* ]] && [[ "$kiwi_profiles" != *"KDE"* ]] && [[ "$kiwi_profiles" != *"COSMIC"* ]]; then
		## Enable initial-setup
		systemctl enable initial-setup.service
		## Enable reconfig mode
		touch /etc/reconfigSys
	fi
fi

#======================================
# Setup default target
#--------------------------------------
if [[ "$kiwi_profiles" != *"Container"* ]] && [[ "$kiwi_profiles" != *"FEX"* ]]; then
	if [[ "$kiwi_profiles" == *"Desktop"* ]]; then
		systemctl set-default graphical.target
	else
		systemctl set-default multi-user.target
	fi
fi

#======================================
# Setup default customizations
#--------------------------------------

if [[ "$kiwi_profiles" == *"Disk"* ]]; then
	# Find the architecture we are on
	installarch=$(uname -m)
	# Setup Raspberry Pi firmware
	if [[ $installarch == "aarch64" ]]; then
		cp -a /usr/share/uboot/rpi_arm64/u-boot.bin /boot/efi/rpi-u-boot.bin
	fi
fi

if [[ "$kiwi_profiles" == *"Server"* ]]; then
	# Trigger lvm-devices-import.path and .service to create
	# a new /etc/lvm/devices/system.devices for the root VG.
	rm -f /etc/lvm/devices/system.devices
	touch /etc/lvm/devices/auto-import-rootvg
fi

if [[ "$kiwi_profiles" == *"Azure"* ]]; then
cat > /etc/ssh/sshd_config.d/50-client-alive-interval.conf << EOF
ClientAliveInterval 120
EOF

cat >> /etc/chrony.conf << EOF
# Azure's virtual time source:
# https://docs.microsoft.com/en-us/azure/virtual-machines/linux/time-sync#check-for-ptp-clock-source
refclock PHC /dev/ptp_hyperv poll 3 dpoll -2 offset 0
EOF

# Support Azure's accelerated networking feature; without this the network fails
# to come up. It may need adjustments for additional drivers in the future.
cat > /etc/NetworkManager/conf.d/99-azure-unmanaged-devices.conf << EOF
# Ignore SR-IOV interface on Azure, since it's transparently bonded
# to the synthetic interface
[keyfile]
unmanaged-devices=driver:mlx4_core;driver:mlx5_core
EOF

# Configure DHCP timeout for Azure to retry indefinitely during VM provisioning
cat > /etc/NetworkManager/conf.d/99-azure-dhcp-timeout.conf << EOF
# Azure requires VMs to attempt DHCP for at least 300 seconds during provisioning,
# as that's the upper bound of how long Azure waits to make networking available.
# NetworkManager's ipv4.dhcp-timeout setting accepts 2147483647 as a special value
# representing infinity, which ensures DHCP keeps retrying indefinitely. This is
# more robust than a fixed timeout and matches systemd-networkd's default behavior.
# Both IPv4 and IPv6 are configured to prepare for IPv6-only scenarios.
# Reference: https://networkmanager.dev/docs/api/latest/nm-settings-nmcli.html
[connection]
ipv4.dhcp-timeout=2147483647
ipv6.dhcp-timeout=2147483647
EOF
fi

if [[ "$kiwi_profiles" == *"GCE"* ]]; then
cat <<EOF > /etc/NetworkManager/conf.d/gcp-mtu.conf
# In GCP it is recommended to use 1460 as the MTU.
# Set it to 1460 for all connections.
# https://cloud.google.com/network-connectivity/docs/vpn/concepts/mtu-considerations
[connection]
ethernet.mtu = 1460
EOF
fi

if [[ "$kiwi_profiles" == *"Vagrant"* ]]; then
sed -e 's/.*UseDNS.*/UseDNS no/' -i /etc/ssh/sshd_config
mkdir -m 0700 -p ~vagrant/.ssh
cat > ~vagrant/.ssh/authorized_keys << EOKEYS
ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEA6NF8iallvQVp22WDkTkyrtvp9eWW6A8YVr+kz4TjGYe7gHzIw+niNltGEFHzD8+v1I2YJ6oXevct1YeS0o9HZyN1Q9qgCgzUFtdOKLv6IedplqoPkcmF0aYet2PkEDo3MlTBckFXPITAMzF8dJSIFo9D8HfdOV0IAdx4O7PtixWKn5y2hMNG0zQPyUecp4pzC6kivAIhyfHilFR61RGL+GPXQ2MWZWFYbAGjyiYJnAmCP3NOTd0jMZEnDkbUvxhMmBYSdETk1rRgm+R4LOzFUGaHqHDLKLX+FIPKcF96hrucXzcWyLbIbEgE98OHlnVYCzRdK8jlqm8tehUc9c9WhQ== vagrant insecure public key
EOKEYS
chmod 600 ~vagrant/.ssh/authorized_keys
chown -R vagrant:vagrant ~vagrant/.ssh/

cat > /etc/sudoers.d/vagrant << EOSUDOER
## Ensure the vagrant user always can use sudo
Defaults:vagrant !requiretty
vagrant ALL=(ALL) NOPASSWD: ALL
EOSUDOER
chmod 600 /etc/sudoers.d/vagrant

cat > /etc/ssh/sshd_config.d/10-vagrant-insecure-rsa-key.conf <<EOF
# For now the vagrant insecure key is an rsa key
# https://github.com/hashicorp/vagrant/issues/11783
PubkeyAcceptedKeyTypes=+ssh-rsa
EOF

# Further suggestion from @purpleidea (James Shubin) - extend key to root users as well
mkdir -m 0700 -p /root/.ssh
cp /home/vagrant/.ssh/authorized_keys /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chown -R root:root /root/.ssh
fi

# https://bugzilla.redhat.com/show_bug.cgi?id=2356069
if [[ "$kiwi_profiles" == *"Container"* ]] && [[ "$kiwi_profiles" != *"Init"* ]]; then
	if [[ -f /usr/lib/tmpfiles.d/rootfiles.conf ]]; then
		systemd-tmpfiles --create /usr/lib/tmpfiles.d/rootfiles.conf
	fi
fi

if [[ "$kiwi_profiles" == *"Container"* ]] || [[ "$kiwi_profiles" == *"FEX"* ]]; then
	# Set install langs macro so that new rpms that get installed will
	# only install langs that we limit it to.
	LANG="en_US"
	echo "%_install_langs $LANG" > /etc/rpm/macros.image-language-conf

	# https://bugzilla.redhat.com/show_bug.cgi?id=1727489
	echo 'LANG="C.UTF-8"' >  /etc/locale.conf

	# https://bugzilla.redhat.com/show_bug.cgi?id=1400682
	echo "Import RPM GPG key"
	releasever=$(rpm --eval '%{?fedora}')

	# When building ELN containers, we don't have the %{fedora} macro
	if [ -z $releasever ]; then
		releasever=eln
	fi

	rpm --import /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-$releasever-primary

	echo "# fstab intentionally empty for containers" > /etc/fstab

	# Remove machine-id on pre generated images
	rm -f /etc/machine-id
	touch /etc/machine-id
	chmod 0644 /etc/machine-id

	echo "# resolv placeholder" > /etc/resolv.conf
	chmod 644 /etc/resolv.conf

	# Remove extraneous files
	rm -rf /tmp/*

	# https://pagure.io/atomic-wg/issue/308
	printf "tsflags=nodocs\n" >>/etc/dnf/dnf.conf

	if [[ "$kiwi_profiles" == *"Base-Generic-Minimal"* ]]; then
		# remove some random help txt files
		rm -fv /usr/share/gnupg/help*.txt

		# Pruning random things
		rm /usr/lib/rpm/rpm.daily
		rm -rfv /usr/lib64/nss/unsupported-tools/  # unsupported

		# Statically linked crap
		rm -fv /usr/sbin/{glibc_post_upgrade.x86_64,sln}
		ln /usr/bin/ln usr/sbin/sln

		# Remove some dnf info
		rm -rfv /var/lib/dnf

		# don't need icons
		rm -rfv /usr/share/icons/*

		#some random not-that-useful binaries
		rm -fv /usr/bin/pinky

		# we lose presets by removing /usr/lib/systemd but we do not care
		rm -rfv /usr/lib/systemd
	fi
	if [[ "$kiwi_profiles" == *"Toolbox"* ]]; then
		# Remove macros.image-language-conf file
		rm -f /etc/rpm/macros.image-language-conf

		# Remove 'tsflags=nodocs' line from dnf.conf
		sed -i '/tsflags=nodocs/d' /etc/dnf/dnf.conf
	fi
fi

if [[ "$kiwi_profiles" == *"Jam"* ]]; then
# Override boot configuration in Anaconda to enable threaded IRQs
cat > /usr/share/anaconda/post-scripts/85-jam-threadirqs.ks << THREADIRQS_EOF
%post

echo "Enable threaded IRQs"
grubby --update-kernel=ALL --args="threadirqs"
%end
THREADIRQS_EOF

# Override new user configuration to add audio groups
sed -e "s/UserGroups=.*/UserGroups=wheel,jackuser,audio/" -i /etc/xdg/plasmasetuprc

# Override livesys-kde settings
cat >> /var/lib/livesys/livesys-session-extra << EOF

#setup kickoff favorites
/bin/mkdir -p /etc/skel/.config

JAMFAVORITES=/usr/share/applications/firefox.desktop,/usr/share/applications/mozilla-thunderbird.desktop,/usr/share/applications/studio-controls.desktop,/usr/share/applications/ardour6.desktop,/usr/share/applications/carla.desktop,/usr/share/applications/org.kde.konsole.desktop,/usr/share/applications/org.kde.dolphin.desktop,/usr/share/applications/systemsettings.desktop
JAMFAVORITESLIVE=/usr/share/applications/liveinst.desktop,\$JAMFAVORITES

cat <<FOE  >> /etc/skel/.config/kickoffrc
[Favorites]
FavoriteURLs=\$JAMFAVORITES
FOE

/usr/sbin/usermod -a -G jackuser,audio liveuser
EOF
fi

if [[ "$kiwi_profiles" == *"Robotics"* ]]; then

# Extend the post-configuration from the live-desktop, set default shortcuts to IDEs
cat >> /var/lib/livesys/livesys-session-extra << EOF
# disable screensaver locking
cat >> /usr/share/glib-2.0/schemas/org.gnome.desktop.screensaver.gschema.override << FOE
[org.gnome.desktop.screensaver]
lock-enabled=false
FOE

# and hide the lock screen option
cat >> /usr/share/glib-2.0/schemas/org.gnome.desktop.lockdown.gschema.override << FOE
[org.gnome.desktop.lockdown]
disable-lock-screen=true
FOE

# make the installer show up
if [ -f /usr/share/applications/liveinst.desktop ]; then
  # Show harddisk install in shell dash
  sed -i -e 's/NoDisplay=true/NoDisplay=false/' /usr/share/applications/liveinst.desktop ""
  # need to move it to anaconda.desktop to make shell happy
  mv /usr/share/applications/liveinst.desktop /usr/share/applications/anaconda.desktop

  cat >> /usr/share/glib-2.0/schemas/org.gnome.shell.gschema.override << FOE
[org.gnome.shell]
favorite-apps=['org.mozilla.firefox.desktop', 'org.qt-project.qtcreator.desktop', 'arduino.desktop', 'gnome-terminal.desktop','nautilus.desktop', 'anaconda.desktop']
FOE

fi

# rebuild schema cache with any overrides we installed
glib-compile-schemas /usr/share/glib-2.0/schemas

EOF

fi

if [[ "$kiwi_profiles" == *"Design_suite"* ]]; then
# Add link to lists of tutorials
cat >> /usr/share/applications/list-design-tutorials.desktop << FOE
[Desktop Entry]
Name=List of design tutorials
GenericName=List of Tutorials for Designers
Comment=Reference of Design Related Tutorials
Exec=xdg-open https://fedoraproject.org/wiki/Design_Suite/Tutorials
Type=Application
Icon=applications-graphics
Categories=Graphics;Documentation;
FOE
chmod a+x /usr/share/applications/list-design-tutorials.desktop

# Add information about Fedora Design Suite
cat >> /usr/share/applications/fedora-design-suite.desktop << FOE
[Desktop Entry]
Name=Design Suite Info
GenericName=About Design Suite
Comment=Wiki page of Design Suite
Exec=xdg-open https://fedoraproject.org/wiki/Design_Suite
Type=Application
Icon=applications-internet
Categories=Documentation;
FOE
chmod a+x /usr/share/applications/fedora-design-suite.desktop

# Add information about Fedora Design Team
cat >> /usr/share/applications/fedora-design-team.desktop << FOE
[Desktop Entry]
Name=Design Team Info
GenericName=About Design Team
Comment=Documentation about Design Team
Exec=xdg-open https://docs.fedoraproject.org/en-US/design/
Type=Application
Icon=applications-internet
Categories=Documentation;
FOE
chmod a+x /usr/share/applications/fedora-design-team.desktop

# Use Powerline in bash
cat >>  /etc/profile.d/powerline-shell.sh << FOE
# Enable powerline daemon
if [ -f `which powerline-daemon` ]; then
  powerline-daemon -q
  POWERLINE_BASH_CONTINUATION=1
  POWERLINE_BASH_SELECT=1
  . /usr/share/powerline/bash/powerline.sh
fi
FOE
chmod 644 /etc/profile.d/powerline-shell.sh
# End powerline override

# Override the favorite desktop application in Dash
cat >> /usr/share/glib-2.0/schemas/org.gnome.shell.gschema.override << FOE
[org.gnome.shell]
favorite-apps=['org.mozilla.firefox.desktop', 'shotwell.desktop', 'gimp.desktop', 'darktable.desktop', 'krita.desktop', 'inkscape.desktop', 'blender.desktop', 'libreoffice-writer.desktop', 'scribus.desktop', 'kdenlive.desktop', 'nautilus.desktop', 'anaconda.desktop', 'list-design-tutorials.desktop']
FOE

# Rebuild schema cache with any overrides we installed
glib-compile-schemas /usr/share/glib-2.0/schemas
fi

if [[ "$kiwi_profiles" == *"SoaS"* ]]; then
# Get proper release naming in the control panel
cat >> /boot/olpc_build << EOF
Sugar on a Stick
EOF
cat /etc/fedora-release >> /boot/olpc_build

# Set the default Plymouth theme to the Sugar Desktop one
/usr/sbin/plymouth-set-default-theme sugar

# Fix https://bugzilla.redhat.com/show_bug.cgi?id=2239137
cat > /etc/xdg/autostart/xfce-polkit.desktop <<EOF
[Desktop Entry]
Type=Application
Name=xfce-polkit
Exec=/usr/libexec/xfce-polkit
EOF

fi

#======================================
# Set the WSL name for ELN
#--------------------------------------
if [[ "$kiwi_profiles" == *"WSL"* ]] && [[ "$kiwi_iname" == *"ELN"* ]]; then
wsl-setup --name Fedora-ELN
fi

#======================================
# Finalization steps
#--------------------------------------
# Inhibit the ldconfig cache generation unit, see rhbz2348669
touch -r "/usr" "/etc/.updated" "/var/.updated"

if [[ "$kiwi_profiles" == *"FEX"* ]]; then
	# Remove most things except libraries used by FEX and wine stuff.
	# Most binaries that are present in non-x86 architectures should be removed,
	# so they do not run under emulation.

	# rm mingw static libs and headers
	rm -rf /usr/{x86_64,i686}-w64-mingw32/sys-root/mingw/{lib,include}

	# rm everything in libexec
	rm -rf /usr/libexec

	# rm everything in /usr/share except wine and mesa related stuff
	find /usr/share -mindepth 1 -maxdepth 1 \
		\! -name wine -a \
		\! -name mesa-demos -a \
		\! -name drirc.d -a \
		\! -name vulkan \
		\! -name licenses \
		-exec rm -rf {} \;

	# rm everything in /etc except /etc/alternatives and ld stuff
	find /etc -mindepth 1 -maxdepth 1 \
		\! -name alternatives -a \
		\! -name 'ld.so*' -a \
		\! -name '*.kiwi' \
		-exec rm -rf {} \;

	# rm non-libs in lib/lib64
	rm -rf /usr/{lib,lib64}/{locale,tmpfiles.d,systemd,modprobe.d,kbd,cmake}
	rm -rf /usr/{lib,lib64}/python*

	# lib/clc and lib64/clc are identical, replace with a symlink
	rm -rf /usr/lib/clc
	ln -s ../lib64/clc /usr/lib/clc

	# rm sbin except for ldconfig, we don't even have root in some setups
	find /usr/sbin -mindepth 1 -maxdepth 1 \
		\! -name 'ldconfig' \
		-exec rm -rf {} \;

	# rm misc stuff
	rm -rf /usr/{include,games,local,src,tmp}

	# Finally, remove most binaries except Wine stuff, Mesa stuff, the shell,
	# path-related stuff, and system info tools.
	find /usr/bin -mindepth 1 -maxdepth 1 \
		\! -name 'wine*' -a \
		\! -name 'mango*' -a \
		\! -name notepad -a \
		\! -name 'msi*' -a \
		\! -name regedit -a \
		\! -name regsvr32 -a \
		\! -name 'vulkan*' -a \
		\! -name 'vk*' -a \
		\! -name clinfo -a \
		\! -name eglinfo -a \
		\! -name glxinfo -a \
		\! -name ulimit -a \
		\! -name ldd -a \
		\! -name env -a \
		\! -name sh -a \
		\! -name bash -a \
		\! -name ls -a \
		\! -name stat -a \
		\! -name dirname -a \
		\! -name realpath -a \
		\! -name readlink -a \
		\! -name basename -a \
		\! -name nproc -a \
		\! -name uname -a \
		\! -name arch -a \
		\! -name rm \
		-exec rm -rf {} \;

	# Do this last for obvious reasons.
	rm /usr/bin/rm
fi

exit 0
