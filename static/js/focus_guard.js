(() => {
  const cfg = window.UCEBNICE_FOCUS_GUARD;

  // Ochrana se spustí pouze na stránce lekce,
  // kde server předal druh lekce a její klíč.
  if (!cfg || !cfg.kind || !cfg.key) {
    return;
  }

  const storageKey = `ucebnice-focus-${cfg.kind}-${cfg.key}`;

  const MIN_AWAY_MS = 15000;

  let finished = false;
  let sending = false;
  let lastLossAt = 0;
  let awayStartedAt = null;

  const localCount = () =>
    Number(sessionStorage.getItem(storageKey) || 0);

  const setLocalCount = (value) =>
    sessionStorage.setItem(storageKey, String(value));

  async function registerLoss() {
    const now = Date.now();

    // Zabrání dvojímu odeslání stejného opuštění.
    if (finished || sending || now - lastLossAt < 1200) {
      return;
    }

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

      if (!response.ok || !data.ok) {
        console.error('Chyba ochrany:', data);
        return;
      }

      const count = Number(data.count || localCount() + 1);
      setLocalCount(count);

      if (data.terminated) {
        finished = true;

        window.location.replace(
          data.redirect || '/lesson-ukoncena'
        );
        return;
      }

      if (count === 1) {
        alert(
          '⚠️ Varování 1/2\n\n' +
          'Byl(a) jsi mimo stránku alespoň 15 sekund.\n' +
          'Při třetím započítaném opuštění bude lekce ukončena.'
        );
      }

      if (count === 2) {
        alert(
          '⛔ Varování 2/2\n\n' +
          'Ještě jedno opuštění stránky na alespoň 15 sekund ' +
          'způsobí ukončení lekce.'
        );
      }
    } catch (error) {
      console.error('Ochranu se nepodařilo odeslat:', error);
    } finally {
      sending = false;
    }
  }

  function startAwayTimer() {
    if (finished || awayStartedAt !== null) {
      return;
    }

    awayStartedAt = Date.now();
  }

  function finishAwayTimer() {
    if (finished || awayStartedAt === null) {
      return;
    }

    const awayDuration = Date.now() - awayStartedAt;
    awayStartedAt = null;

    if (awayDuration >= MIN_AWAY_MS) {
      registerLoss();
    }
  }

  // Přepnutí na jinou kartu nebo minimalizování prohlížeče.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      startAwayTimer();
    } else {
      finishAwayTimer();
    }
  });

  // Přepnutí do jiné desktopové aplikace.
  window.addEventListener('blur', () => {
    startAwayTimer();
  });

  // Návrat do okna prohlížeče.
  window.addEventListener('focus', () => {
    if (!document.hidden) {
      finishAwayTimer();
    }
  });

  // Normální odeslání lekce se nepovažuje za opuštění.
  document.addEventListener(
    'submit',
    () => {
      finished = true;
    },
    true
  );

  // Normální kliknutí na odkaz uvnitř aplikace.
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

  // Dokončení interaktivní lekce.
  const originalFetch = window.fetch;

  window.fetch = async (...args) => {
    const response = await originalFetch(...args);

    try {
      const requestUrl = String(
        args[0] instanceof Request ? args[0].url : args[0]
      );

      if (
        cfg.kind === 'interactive' &&
        requestUrl.includes('/complete')
      ) {
        finished = true;
        sessionStorage.removeItem(storageKey);
      }
    } catch (error) {
      console.error(error);
    }

    return response;
  };
})();
