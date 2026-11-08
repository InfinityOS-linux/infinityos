(() => {
    'use strict';

    const intro = document.querySelector('#infinityos-installer-intro');
    if (!intro)
        return;

    const app = document.querySelector('#app');
    const frames = [...intro.querySelectorAll('.infinityos-intro-frame')];
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
    const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
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
            const duration = reducedMotion ? 300 : 1300;
            const gap = reducedMotion ? 0 : 400;
            const storageKey = 'infinityos-installer-intro-start';
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
            for (let index = 0; index < frames.length; index++) {
                const offset = index * (duration + gap);
                const elapsed = Date.now() - startedAt;
                if (elapsed < offset)
                    await pause(offset - elapsed);
                const remaining = offset + duration - (Date.now() - startedAt);
                if (remaining <= 0)
                    continue;
                if (index < frames.length - 1) {
                    await show(frames[index], remaining);
                } else {
                    frames[index].classList.add('is-visible');
                    frames[index].setAttribute('aria-hidden', 'false');
                    await pause(remaining);
                }
            }
            await waitForWizard();
            intro.classList.add('is-finished');
            await pause(reducedMotion ? 0 : 450);
        } finally {
            intro.remove();
            app.inert = false;
            window.infinityosInstallerIntroComplete = true;
            window.dispatchEvent(new Event('infinityos-installer-intro-complete'));
        }
    })().catch(console.error);
})();
