/* Internationalisation FR/EN commune au pupitre et au Studio. */
(() => {
  const STORAGE_KEY = 'deckedge.lang';
  const messages = {
    fr: {
      'language.switch': 'Passer en anglais',
      'language.button': 'EN',
      'phone.install.title': 'Garder ce Deck sur mon téléphone',
      'phone.install.intro': 'Après ce premier scan, ajoutez cette page à l’écran d’accueil ou aux favoris. Vous retrouverez ce PC sans recopier le lien ni scanner à chaque démarrage.',
      'phone.install.ios': 'iPhone : Partager → Sur l’écran d’accueil. Android : menu du navigateur → Ajouter à l’écran d’accueil. Gardez DeckEdge ouvert sur le PC et utilisez le même réseau privé.',
      'phone.install.dismiss': 'Compris',
      'deck.monitoring': 'Mesures du PC',
      'deck.mute': 'Activer ou couper le son',
      'deck.muted': 'MUTÉ',
      'deck.output': 'SORTIE',
      'deck.master': 'MASTER',
      'deck.app': 'APP',
      'deck.steps': '{count} ÉTAPES',
      'deck.sensors.connected': 'Capteurs intégrés connectés',
      'deck.sensors.unavailable': 'Mesures indisponibles',
      'deck.volume': 'Volume',
      'deck.addPage': 'Ajouter une Page',
    },
    en: {
      'language.switch': 'Switch to French',
      'language.button': 'FR',
      'phone.install.title': 'Keep this Deck on your phone',
      'phone.install.intro': 'After this first scan, add this page to your home screen or bookmarks. You will find this PC again without copying the link or scanning at every startup.',
      'phone.install.ios': 'iPhone: Share → Add to Home Screen. Android: browser menu → Add to Home screen. Keep DeckEdge open on the PC and use the same private network.',
      'phone.install.dismiss': 'Got it',
      'deck.monitoring': 'PC measurements',
      'deck.mute': 'Mute or unmute',
      'deck.muted': 'MUTED',
      'deck.output': 'OUTPUT',
      'deck.master': 'MASTER',
      'deck.app': 'APP',
      'deck.steps': '{count} STEPS',
      'deck.sensors.connected': 'Integrated sensors connected',
      'deck.sensors.unavailable': 'Measurements unavailable',
      'deck.volume': 'Volume',
      'deck.addPage': 'Add a Page',
    },
  };

  const supported = Object.keys(messages);
  const listeners = [];

  function normalize(value) {
    const language = String(value || '').toLowerCase();
    return language.startsWith('fr') ? 'fr' : 'en';
  }

  function detect() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (supported.includes(saved)) return saved;
    } catch {}
    return normalize(navigator.language || navigator.userLanguage || 'en');
  }

  let language = detect();

  function t(key, values = {}) {
    const table = messages[language] || messages.en;
    const fallback = messages.en;
    let text = table[key] ?? fallback[key] ?? key;
    return String(text).replace(/\{(\w+)\}/g, (match, name) =>
      Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : match
    );
  }

  function apply(root = document) {
    document.documentElement.lang = language;
    root.querySelectorAll('[data-i18n]').forEach(element => {
      element.textContent = t(element.dataset.i18n);
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
      element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder));
    });
    root.querySelectorAll('[data-i18n-title]').forEach(element => {
      element.setAttribute('title', t(element.dataset.i18nTitle));
    });
    root.querySelectorAll('[data-i18n-aria-label]').forEach(element => {
      element.setAttribute('aria-label', t(element.dataset.i18nAriaLabel));
    });
  }

  function setLanguage(next) {
    const value = supported.includes(next) ? next : 'en';
    if (value === language) return;
    language = value;
    try { localStorage.setItem(STORAGE_KEY, language); } catch {}
    apply();
    listeners.forEach(listener => {
      try { listener(language); } catch (error) { console.error(error); }
    });
  }

  function toggleLanguage() {
    setLanguage(language === 'fr' ? 'en' : 'fr');
  }

  function onChange(listener) {
    if (typeof listener === 'function') listeners.push(listener);
  }

  apply();
  window.addEventListener('DOMContentLoaded', () => apply());
  window.I18n = {
    get lang() { return language; },
    t,
    apply,
    setLanguage,
    toggleLanguage,
    onChange,
  };
})();
