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
        await pause(reducedMotion ? 0 : 620);
    }

    (async () => {
        try {
            await waitForWizard();
            await show(frames[0], reducedMotion ? 300 : 2800);
            await show(frames[1], reducedMotion ? 300 : 2600);
            frames[2].classList.add('is-visible');
            frames[2].setAttribute('aria-hidden', 'false');
            await pause(reducedMotion ? 300 : 3000);
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
