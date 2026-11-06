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

    function waitForWizard() {
        return new Promise(resolve => {
            const ready = () => document.querySelector('#installation-wizard');
            if (ready()) {
                resolve();
                return;
            }
            const observer = new MutationObserver(() => {
                if (!ready())
                    return;
                observer.disconnect();
                clearTimeout(timeout);
                resolve();
            });
            observer.observe(app, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] });
            const timeout = setTimeout(() => {
                observer.disconnect();
                resolve();
            }, 20000);
        });
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
            let startedAt = Date.now();
            try {
                const saved = Number(window.sessionStorage.getItem(storageKey));
                if (saved > 0)
                    startedAt = saved;
                else
                    window.sessionStorage.setItem(storageKey, String(startedAt));
            } catch (_) {
                // Private storage can be unavailable; the intro still runs for this page.
            }
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
