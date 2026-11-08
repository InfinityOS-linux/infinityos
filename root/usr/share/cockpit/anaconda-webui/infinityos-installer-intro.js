(() => {
    'use strict';

    const intro = document.querySelector('#infinityos-installer-intro');
    if (!intro)
        return;

    const app = document.querySelector('#app');
    const frames = [...intro.querySelectorAll('.infinityos-intro-frame')];
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
    const timing = reducedMotion ? [300, 300, 300] : [2800, 2600, 3000];
    const gap = reducedMotion ? 0 : 620;
    const storageKey = 'infinityos-installer-intro-start';
    app.inert = true;
    let startedAt = 0;
    try {
        const saved = Number(window.localStorage.getItem(storageKey));
        if (saved > 0 && saved <= Date.now())
            startedAt = saved;
    } catch (_) {
        // Storage may be unavailable in private sessions.
    }

    async function waitForWizard() {
        const ready = () => document.querySelector(startedAt ? '#installation-wizard'
            : '#installation-wizard.anaconda-wizard-step-anaconda-screen-language');
        while (true) {
            if (!ready()) {
                const appeared = await new Promise(resolve => {
                    const finish = available => {
                        observer.disconnect();
                        clearTimeout(timeout);
                        resolve(available);
                    };
                    const observer = new MutationObserver(() => {
                        if (ready())
                            finish(true);
                    });
                    // Do not hide Anaconda errors behind a permanent preloader.
                    const timeout = setTimeout(() => finish(false), 20000);
                    observer.observe(app, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
                });
                if (!appeared)
                    return false;
            }
            // Anaconda mounts the language page once before its own locale reload.
            await pause(1500);
            if (ready())
                return true;
        }
    }

    async function show(frame, duration) {
        frame.classList.add('is-visible');
        frame.setAttribute('aria-hidden', 'false');
        await pause(duration);
        frame.classList.remove('is-visible');
        frame.setAttribute('aria-hidden', 'true');
    }

    (async () => {
        try {
            if (!await waitForWizard())
                return;
            intro.classList.add('is-ready');
            await pause(reducedMotion ? 0 : 400);
            if (!startedAt) {
                startedAt = Date.now();
                try {
                    window.localStorage.setItem(storageKey, String(startedAt));
                } catch (_) {
                    // The intro still runs for this page without storage.
                }
            }
            window.dispatchEvent(new Event('infinityos-installer-intro-start'));
            let offset = 0;
            for (let index = 0; index < frames.length; index++) {
                const elapsed = Date.now() - startedAt;
                if (elapsed < offset)
                    await pause(offset - elapsed);
                const remaining = offset + timing[index] - (Date.now() - startedAt);
                if (remaining > 0)
                    await show(frames[index], remaining);
                offset += timing[index] + (index < frames.length - 1 ? gap : 0);
            }
            intro.classList.add('is-finished');
            await pause(reducedMotion ? 0 : 800);
        } finally {
            intro.remove();
            app.inert = false;
            window.infinityosInstallerIntroComplete = true;
            window.dispatchEvent(new Event('infinityos-installer-intro-complete'));
        }
    })().catch(console.error);
})();
