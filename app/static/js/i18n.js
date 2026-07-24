let currentLanguage = localStorage.getItem('language') || 'en';
let translations = {};

const langLabels = {
    'en': 'English',
    'ta': 'தமிழ்',
    'hi': 'हिन्दी',
    'te': 'తెలుగు'
};

async function loadTranslations(lang) {
    try {
        const response = await fetch(`/static/locales/${lang}.json`);
        if (!response.ok) throw new Error(`Could not load translations for ${lang}`);
        translations = await response.json();
        currentLanguage = lang;
        localStorage.setItem('language', lang);
        
        // Update selector label if it exists
        const labelEl = document.getElementById('current-lang-label');
        if (labelEl) {
            labelEl.textContent = langLabels[lang] || 'English';
        }
        
        applyTranslations();
        
        // Dispatch custom event for dynamically loaded pages or custom scripts (like POS)
        document.dispatchEvent(new CustomEvent('languageChanged', { detail: { lang, translations } }));
    } catch (error) {
        console.error("i18n loading error:", error);
    }
}

function applyTranslations() {
    // 1. Text content translation
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[key]) {
            // Keep icon span if present
            const iconSpan = el.querySelector('span');
            if (iconSpan) {
                // If it has an icon, only replace the text part
                const iconHtml = iconSpan.outerHTML;
                el.innerHTML = iconHtml + " " + translations[key];
            } else {
                el.textContent = translations[key];
            }
        }
    });

    // 2. Input Placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (translations[key]) {
            el.setAttribute('placeholder', translations[key]);
        }
    });

    // 3. Buttons or Inputs with value attributes
    document.querySelectorAll('[data-i18n-value]').forEach(el => {
        const key = el.getAttribute('data-i18n-value');
        if (translations[key]) {
            el.value = translations[key];
        }
    });
}

function t(key) {
    return translations[key] || key;
}

async function changeLanguage(lang) {
    // Instantly apply client-side
    await loadTranslations(lang);
    
    // Sync with backend database
    try {
        await fetch('/update_language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ language: lang })
        });
    } catch (e) {
        console.warn("Could not synchronize language preference with backend:", e);
    }
}

// Automatically load preferred language
document.addEventListener("DOMContentLoaded", () => {
    // Check if lang is injected in HTML tag, else fallback to localStorage or default 'en'
    const htmlLang = document.documentElement.getAttribute('lang') || 'en';
    loadTranslations(htmlLang);
});
