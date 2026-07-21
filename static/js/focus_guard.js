(() => {
  const cfg = window.UCEBNICE_FOCUS_GUARD;
  if (!cfg || !cfg.kind || !cfg.key) return;

  const storageKey = `ucebnice-focus-${cfg.kind}-${cfg.key}`;
  let finished = false;
  let sending = false;
  let lastLossAt = 0;
  let awayStartedAt = null;

  const MIN_AWAY_MS = 15000;

  const localCount = () => Number(sessionStorage.getItem(storageKey) || 0);
  const setLocalCount = (value) =>
    sessionStorage.setItem(storageKey, String(value));

  async function registerLoss() {
    const now = Date.now();

    if (finished || sending || now - lastLossAt < 1200) return;

    lastLossAt = now;
    sending = true;

    try {
      const response = await fetch('/api/focus-lost', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          kind: cfg.kind,
          key: String(cfg.key)
        }),
        credentials: 'same-origin',
        keepalive: true
      });

      const data = await response.json();

      if (!data.ok) return;

      setLocalCount(data.count || localCount() + 1);

      if (data.terminated) {
        finished = true;
        window.location.replace(data.redirect || '/lesson-ukoncena');
        return;
      }

      if (data.count === 1) {
        alert(
          '⚠️ Varování 1/2\n' +
          'Byl(a) jsi mimo stránku alespoň 15 sekund. ' +
          'Při třetím opuštění bude lekce automaticky ukončena.'
        );
      } else if (data.count === 2) {
        alert(
          '⛔ Varování 2/2\n' +
          'Ještě jedno opuštění stránky na alespoň 15 sekund ' +
          'způsobí automatické ukončení lekce.'
        );
      }
    } catch (error) {
      setLocalCount(Math.min(3, localCount() + 1));
    } finally {
      sending = false;
    }
  }

  function startAwayTimer() {
    if (finished || awayStartedAt !== null) return;
    awayStartedAt = Date.now();
  }

  function finishAwayTimer() {
    if (finished || awayStartedAt === null) return;

    const awayDuration = Date.now() - awayStartedAt;
    awayStartedAt = null;

    if (awayDuration >= MIN_AWAY_MS) {
      registerLoss();
    }
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      startAwayTimer();
    } else {
      finishAwayTimer();
    }
  });

  window.addEventListener('blur', () => {
    startAwayTimer();
  });

  window.addEventListener('focus', () => {
    if (!document.hidden) {
      finishAwayTimer();
    }
  });

  document.addEventListener(
    'submit',
    () => {
      finished = true;
    },
    true
  );

  document.addEventListener(
    'click',
    (event) => {
      const link = event.target.closest('a');

      if (
        link &&
        link.href &&
        new URL(link.href, location.href).origin === location.origin
      ) {
        finished = true;
      }
    },
    true
  );

  const originalFetch = window.fetch;

  window.fetch = async (...args) => {
    const response = await originalFetch(...args);

    try {
      const url = String(
        args[0] instanceof Request ? args[0].url : args[0]
      );

      if (cfg.kind === 'interactive' && url.includes('/complete')) {
        finished = true;
        sessionStorage.removeItem(storageKey);
      }
    } catch (_) {}

    return response;
  };
})();
