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

    async function waitForWizard() {
        const ready = () => document.querySelector('#installation-wizard.anaconda-wizard-step-anaconda-screen-language');
        while (true) {
            if (!ready())
                await new Promise(resolve => {
                    const observer = new MutationObserver(() => {
                        if (!ready())
                            return;
                        observer.disconnect();
                        resolve();
                    });
                    observer.observe(app, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
                });
            // Anaconda mounts the language page once before its own locale reload.
            await pause(1500);
            if (ready())
                return;
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
            await waitForWizard();
            intro.classList.add('is-ready');
            await pause(reducedMotion ? 0 : 400);
            let startedAt = Date.now();
            try {
                const saved = Number(window.localStorage.getItem(storageKey));
                if (saved > 0 && saved <= startedAt)
                    startedAt = saved;
                else
                    window.localStorage.setItem(storageKey, String(startedAt));
            } catch (_) {
                // Private storage can be unavailable; the intro still runs for this page.
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
