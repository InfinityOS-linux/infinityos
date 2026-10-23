/* Installer music and controls remain mounted while Anaconda changes steps. */
(() => {
    'use strict';

    if (window.infinityosInstallerAudio)
        return;
    window.infinityosInstallerAudio = true;

    const fadeSeconds = 14;
    const track = new URL('infinityos-installer-music.mp3', document.currentScript.src);
    const audio = document.createElement('audio');
    audio.src = track.href;
    audio.preload = 'none';
    audio.loop = true;
    audio.volume = 0;
    audio.hidden = true;
    document.body.append(audio);

    const controls = document.createElement('div');
    controls.className = 'infinityos-installer-audio';
    controls.hidden = true;
    controls.innerHTML = `
        <button class="infinityos-audio-button infinityos-audio-mute" type="button" aria-pressed="false">
            <svg class="infinityos-audio-sound" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 9v6h4l5 4V5L8 9H4Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
                <path d="M16 9a4 4 0 0 1 0 6m2.5-8.5a7.5 7.5 0 0 1 0 11" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
            <svg class="infinityos-audio-muted" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 9v6h4l5 4V5L8 9H4Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
                <path d="m17 9 5 6m0-6-5 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
            </svg>
        </button>
        <button class="infinityos-audio-button infinityos-audio-volume" type="button" aria-expanded="false" aria-controls="infinityos-audio-popover">
            <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M5 5v14m7-9v9m7-14v14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                <circle cx="5" cy="10" r="2" fill="currentColor"/><circle cx="12" cy="7" r="2" fill="currentColor"/><circle cx="19" cy="13" r="2" fill="currentColor"/>
            </svg>
        </button>
        <div class="infinityos-audio-popover" id="infinityos-audio-popover" hidden>
            <label for="infinityos-audio-level"></label>
            <div class="infinityos-audio-slider-row">
                <input id="infinityos-audio-level" type="range" min="0" max="100" value="45">
                <output for="infinityos-audio-level">45%</output>
            </div>
        </div>`;
    document.body.append(controls);

    const muteButton = controls.querySelector('.infinityos-audio-mute');
    const volumeButton = controls.querySelector('.infinityos-audio-volume');
    const popover = controls.querySelector('.infinityos-audio-popover');
    const slider = controls.querySelector('input');
    const output = controls.querySelector('output');
    const label = controls.querySelector('label');
    let level = 45;
    let lastNonZeroLevel = level;
    let muted = false;
    let welcomeReady = false;
    let volumeTimer;

    function updateLabels() {
        const locale = document.documentElement.lang || navigator.language || 'en';
        const polish = locale.toLowerCase().startsWith('pl');
        const muteText = polish ? (muted ? 'Włącz dźwięk' : 'Wycisz muzykę')
            : (muted ? 'Unmute music' : 'Mute music');
        const volumeText = polish ? 'Głośność muzyki' : 'Music volume';
        muteButton.setAttribute('aria-label', muteText);
        muteButton.title = muteText;
        volumeButton.setAttribute('aria-label', volumeText);
        volumeButton.title = volumeText;
        label.textContent = volumeText;
    }

    function updateVolume() {
        const fadeIn = Math.min(1, Math.max(0, audio.currentTime / fadeSeconds));
        const fadeOut = Number.isFinite(audio.duration) && audio.duration > 0
            ? Math.min(1, Math.max(0, (audio.duration - audio.currentTime) / fadeSeconds))
            : 1;
        audio.volume = (level / 100) * Math.min(fadeIn, fadeOut);
        audio.muted = muted;
    }

    function updateControls() {
        controls.classList.toggle('is-muted', muted);
        muteButton.setAttribute('aria-pressed', String(muted));
        slider.value = String(level);
        output.value = `${level}%`;
        updateLabels();
        updateVolume();
    }

    function startMusic() {
        if (!welcomeReady || muted || !audio.paused)
            return;
        const attempt = audio.play();
        if (attempt && typeof attempt.then === 'function') {
            attempt.then(() => {
                document.removeEventListener('pointerdown', startMusic, true);
                document.removeEventListener('keydown', startMusic, true);
            }).catch(() => {
                // Browsers requiring a page gesture can start on the first installer action.
            });
        }
    }

    muteButton.addEventListener('click', () => {
        if (muted && level === 0)
            level = lastNonZeroLevel;
        muted = !muted;
        updateControls();
        if (!muted)
            startMusic();
    });

    volumeButton.addEventListener('click', () => {
        popover.hidden = !popover.hidden;
        volumeButton.setAttribute('aria-expanded', String(!popover.hidden));
        if (!popover.hidden)
            slider.focus();
    });

    slider.addEventListener('input', () => {
        level = Number(slider.value);
        if (level > 0)
            lastNonZeroLevel = level;
        muted = level === 0;
        updateControls();
        if (!muted)
            startMusic();
    });

    document.addEventListener('pointerdown', event => {
        if (!controls.contains(event.target) && !popover.hidden) {
            popover.hidden = true;
            volumeButton.setAttribute('aria-expanded', 'false');
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !popover.hidden) {
            popover.hidden = true;
            volumeButton.setAttribute('aria-expanded', 'false');
            volumeButton.focus();
        }
    });

    document.addEventListener('pointerdown', startMusic, true);
    document.addEventListener('keydown', startMusic, true);
    function activateOnWelcome() {
        if (!document.querySelector('#installation-wizard.anaconda-wizard-step-anaconda-screen-language'))
            return;
        welcomeReady = true;
        controls.hidden = false;
        audio.preload = 'auto';
        welcomeObserver.disconnect();
        startMusic();
    }
    const welcomeObserver = new MutationObserver(activateOnWelcome);
    welcomeObserver.observe(document.body, {
        childList: true, subtree: true, attributes: true, attributeFilter: ['class'],
    });
    activateOnWelcome();
    new MutationObserver(updateLabels).observe(document.documentElement, {
        attributes: true, attributeFilter: ['lang'],
    });
    audio.addEventListener('play', () => {
        clearInterval(volumeTimer);
        volumeTimer = setInterval(updateVolume, 100);
    });
    audio.addEventListener('pause', () => clearInterval(volumeTimer));
    window.addEventListener('pagehide', () => {
        clearInterval(volumeTimer);
        audio.pause();
    });
    updateControls();
})();
