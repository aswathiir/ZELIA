import React, { createContext, useContext, useState } from 'react';
import { translations, LANGUAGE_META } from '../utils/translations';

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
    const [language, setLanguage] = useState('English');

    const t = (key) => translations[language]?.[key] ?? translations['English']?.[key] ?? key;

    const meta = LANGUAGE_META[language] || LANGUAGE_META['English'];
    const langCode = meta.code;   // BCP-47, e.g. 'ta-IN' for Speech API

    return (
        <LanguageContext.Provider value={{ language, setLanguage, t, langCode, LANGUAGE_META }}>
            {children}
        </LanguageContext.Provider>
    );
};

export const useLanguage = () => useContext(LanguageContext);
