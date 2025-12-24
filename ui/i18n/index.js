/**
 * AI Publisher Pro - Internationalization (i18n) System
 *
 * Lightweight i18n implementation for Japanese, English, and Vietnamese UI.
 *
 * Usage:
 *   // Initialize (call once on page load)
 *   await i18n.init();
 *
 *   // Get translation
 *   i18n.t('app.title')  // => "出版スタジオ" (if locale is 'ja')
 *
 *   // Change language
 *   await i18n.setLocale('en');
 *
 *   // Apply translations to all elements with data-i18n attribute
 *   i18n.translatePage();
 */

class I18nManager {
  constructor() {
    this.locale = 'vi'; // Default locale
    this.fallbackLocale = 'en';
    this.translations = {};
    this.supportedLocales = ['vi', 'en', 'ja'];
    this.isLoaded = false;
  }

  /**
   * Initialize i18n system
   * @param {string} locale - Initial locale (optional, defaults to saved or browser locale)
   */
  async init(locale = null) {
    // Determine locale priority: param > saved > browser > default
    const savedLocale = localStorage.getItem('ui_language');
    const browserLocale = navigator.language?.split('-')[0];

    this.locale = locale
      || savedLocale
      || (this.supportedLocales.includes(browserLocale) ? browserLocale : 'vi');

    // Load translations
    await this.loadTranslations(this.locale);

    // Load fallback if different
    if (this.locale !== this.fallbackLocale) {
      await this.loadTranslations(this.fallbackLocale);
    }

    this.isLoaded = true;
    console.log(`[i18n] Initialized with locale: ${this.locale}`);

    // Apply translations to page
    this.translatePage();

    // Update HTML lang attribute
    document.documentElement.lang = this.locale;

    return this;
  }

  /**
   * Load translations for a locale
   * @param {string} locale - Locale code
   */
  async loadTranslations(locale) {
    if (this.translations[locale]) {
      return this.translations[locale];
    }

    try {
      // Try to load from /ui/i18n/locales/{locale}.json
      const response = await fetch(`/ui/i18n/locales/${locale}.json`);

      if (!response.ok) {
        throw new Error(`Failed to load ${locale}: ${response.status}`);
      }

      this.translations[locale] = await response.json();
      console.log(`[i18n] Loaded translations for: ${locale}`);
      return this.translations[locale];
    } catch (error) {
      console.warn(`[i18n] Could not load translations for ${locale}:`, error);
      this.translations[locale] = {};
      return {};
    }
  }

  /**
   * Get translation for a key
   * @param {string} key - Dot-notation key (e.g., 'app.title')
   * @param {object} params - Optional parameters for interpolation
   * @returns {string} - Translated string or key if not found
   */
  t(key, params = {}) {
    // Try current locale
    let value = this._getNestedValue(this.translations[this.locale], key);

    // Fallback to fallback locale
    if (value === undefined && this.locale !== this.fallbackLocale) {
      value = this._getNestedValue(this.translations[this.fallbackLocale], key);
    }

    // If still not found, return the key
    if (value === undefined) {
      console.warn(`[i18n] Missing translation: ${key}`);
      return key;
    }

    // Interpolate parameters
    if (params && typeof value === 'string') {
      Object.keys(params).forEach(param => {
        value = value.replace(new RegExp(`{{${param}}}`, 'g'), params[param]);
      });
    }

    return value;
  }

  /**
   * Set locale and reload translations
   * @param {string} locale - New locale code
   */
  async setLocale(locale) {
    if (!this.supportedLocales.includes(locale)) {
      console.warn(`[i18n] Unsupported locale: ${locale}`);
      return false;
    }

    this.locale = locale;
    localStorage.setItem('ui_language', locale);

    // Load if not already loaded
    await this.loadTranslations(locale);

    // Update page
    this.translatePage();

    // Update HTML lang attribute
    document.documentElement.lang = locale;

    // Dispatch event for custom handlers
    window.dispatchEvent(new CustomEvent('languageChanged', { detail: { locale } }));

    console.log(`[i18n] Locale changed to: ${locale}`);
    return true;
  }

  /**
   * Get current locale
   * @returns {string}
   */
  getLocale() {
    return this.locale;
  }

  /**
   * Get all supported locales
   * @returns {string[]}
   */
  getSupportedLocales() {
    return this.supportedLocales;
  }

  /**
   * Translate all elements with data-i18n attribute
   */
  translatePage() {
    // Translate text content
    document.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      const translation = this.t(key);
      if (translation !== key) {
        el.textContent = translation;
      }
    });

    // Translate placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      const translation = this.t(key);
      if (translation !== key) {
        el.placeholder = translation;
      }
    });

    // Translate titles (tooltips)
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      const translation = this.t(key);
      if (translation !== key) {
        el.title = translation;
      }
    });

    // Translate aria-labels
    document.querySelectorAll('[data-i18n-aria]').forEach(el => {
      const key = el.getAttribute('data-i18n-aria');
      const translation = this.t(key);
      if (translation !== key) {
        el.setAttribute('aria-label', translation);
      }
    });
  }

  /**
   * Get nested value from object using dot notation
   * @private
   */
  _getNestedValue(obj, key) {
    if (!obj) return undefined;

    const keys = key.split('.');
    let value = obj;

    for (const k of keys) {
      if (value === undefined || value === null) return undefined;
      value = value[k];
    }

    return value;
  }
}

// Create global instance
const i18n = new I18nManager();

// Export for ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { i18n, I18nManager };
}

// Make available globally
window.i18n = i18n;
