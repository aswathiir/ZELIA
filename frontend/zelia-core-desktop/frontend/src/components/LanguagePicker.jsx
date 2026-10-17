import React from 'react';
import { useLanguage } from '../context/LanguageContext';

/* Inline language switcher that works on both dark and light backgrounds */
const LanguagePicker = ({ dark = false }) => {
    const { language, setLanguage } = useLanguage();

    const LANGS = [
        { code: 'English', label: 'EN', full: 'English' },
        { code: 'Hindi', label: 'हि', full: 'हिन्दी' },
        { code: 'Tamil', label: 'த', full: 'தமிழ்' },
        { code: 'Malayalam', label: 'മ', full: 'മലയാളം' },
    ];

    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {LANGS.map(l => {
                const active = language === l.code;
                return (
                    <button key={l.code} onClick={() => setLanguage(l.code)} title={l.full}
                        style={{
                            padding: '5px 10px', borderRadius: 20, fontSize: 13, fontWeight: 800,
                            cursor: 'pointer', fontFamily: "'Noto Sans', 'Noto Sans Devanagari', 'Noto Sans Tamil', 'Noto Sans Malayalam', sans-serif",
                            transition: 'all .15s',
                            background: active
                                ? (dark ? 'white' : '#0D1B33')
                                : (dark ? 'rgba(255,255,255,.1)' : '#EAF0F7'),
                            color: active
                                ? (dark ? '#060E1F' : 'white')
                                : (dark ? 'rgba(255,255,255,.6)' : '#4F6E96'),
                            border: active
                                ? (dark ? '1.5px solid white' : '1.5px solid #0D1B33')
                                : (dark ? '1.5px solid rgba(255,255,255,.2)' : '1.5px solid #C0D0E0'),
                        }}>
                        {l.label}
                    </button>
                );
            })}
        </div>
    );
};

export default LanguagePicker;
