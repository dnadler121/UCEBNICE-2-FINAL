(() => {
  const cfg = window.UCEBNICE_FOCUS_GUARD;
  if (!cfg || !cfg.kind || !cfg.key) return;

  const storageKey = `ucebnice-focus-${cfg.kind}-${cfg.key}`;
  let finished = false;
  let sending = false;
  let hiddenAt = null;

  const localCount = () => Number(sessionStorage.getItem(storageKey) || 0);
  const setLocalCount = (value) => sessionStorage.setItem(storageKey, String(value));

  async function registerLoss() {
    const now = Date.now();
    if (finished || sending || now - lastLossAt < 1200) return;
    lastLossAt = now;
    sending = true;

    try {
      const response = await fetch('/api/focus-lost', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({kind: cfg.kind, key: String(cfg.key)}),
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
        alert('⚠️ Varování 1/2\nOpustil(a) jsi stránku lekce. Při třetím opuštění bude lekce automaticky ukončena.');
      } else if (data.count === 2) {
        alert('⛔ Varování 2/2\nJeště jedno opuštění stránky způsobí automatické ukončení lekce.');
      }
    } catch (error) {
      setLocalCount(Math.min(3, localCount() + 1));
    } finally {
      sending = false;
    }
  }

  document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    if (!hiddenAt) {
      hiddenAt = Date.now();
    }
    return;
  }

  if (hiddenAt) {
    const secondsAway = (Date.now() - hiddenAt) / 1000;
    hiddenAt = null;

    if (secondsAway >= 15) {
      registerLoss();
    }
  }
  });
  
  window.addEventListener('blur', () => {
    if (!hiddenAt) {
      hiddenAt = Date.now();
    }
  });
  
  window.addEventListener('focus', () => {
    if (!document.hidden && hiddenAt) {
      const secondsAway = (Date.now() - hiddenAt) / 1000;
      hiddenAt = null;
  
      if (secondsAway >= 15) {
        registerLoss();
      }
    }
  });

  document.addEventListener('submit', () => { finished = true; }, true);
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a');
    if (link && link.href && new URL(link.href, location.href).origin === location.origin) {
      finished = true;
    }
  }, true);

  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    try {
      const url = String(args[0] instanceof Request ? args[0].url : args[0]);
      if (cfg.kind === 'interactive' && url.includes('/complete')) {
        finished = true;
        sessionStorage.removeItem(storageKey);
      }
    } catch (_) {}
    return response;
  };
})();
