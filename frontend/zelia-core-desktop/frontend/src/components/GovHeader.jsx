import React from 'react';
import LanguagePicker from './LanguagePicker';
import { useLanguage } from '../context/LanguageContext';

/* ─── Ashoka Emblem SVG (stylised representation) ─── */
const AshokaEmblem = () => (
    <svg width="52" height="60" viewBox="0 0 52 60" fill="none" xmlns="http://www.w3.org/2000/svg" aria-label="Emblem of India">
        {/* Base plate */}
        <rect x="8" y="52" width="36" height="5" rx="1" fill="#8B6914"/>
        {/* Abacus */}
        <rect x="6" y="44" width="40" height="9" rx="2" fill="#C49A22"/>
        {/* Chakra on abacus */}
        <circle cx="26" cy="48" r="3.5" fill="none" stroke="#1B3D6E" strokeWidth="1.2"/>
        <circle cx="26" cy="48" r="1" fill="#1B3D6E"/>
        {[0,30,60,90,120,150,180,210,240,270,300,330].map((deg,i) => {
            const r = deg * Math.PI / 180;
            return <line key={i} x1={26 + 1*Math.cos(r)} y1={48 + 1*Math.sin(r)} x2={26 + 3.2*Math.cos(r)} y2={48 + 3.2*Math.sin(r)} stroke="#1B3D6E" strokeWidth="0.7"/>;
        })}
        {/* Lions body (simplified silhouette) */}
        <ellipse cx="18" cy="33" rx="8" ry="9" fill="#C49A22"/>
        <ellipse cx="34" cy="33" rx="8" ry="9" fill="#C49A22"/>
        {/* Lion heads */}
        <circle cx="18" cy="24" r="6" fill="#C49A22"/>
        <circle cx="34" cy="24" r="6" fill="#C49A22"/>
        {/* Manes */}
        <circle cx="18" cy="23" r="7.5" fill="none" stroke="#8B6914" strokeWidth="2.5"/>
        <circle cx="34" cy="23" r="7.5" fill="none" stroke="#8B6914" strokeWidth="2.5"/>
        {/* Eyes */}
        <circle cx="15.5" cy="22" r="1" fill="#1B3D6E"/>
        <circle cx="36.5" cy="22" r="1" fill="#1B3D6E"/>
        {/* Center top – back lion */}
        <ellipse cx="26" cy="28" rx="6" ry="8" fill="#D4A82A"/>
        <circle cx="26" cy="20" r="5.5" fill="#D4A82A"/>
        <circle cx="26" cy="20" r="7" fill="none" stroke="#8B6914" strokeWidth="2"/>
        <circle cx="24" cy="19" r="1" fill="#1B3D6E"/>
        <circle cx="28" cy="19" r="1" fill="#1B3D6E"/>
        {/* Satyameva Jayate motto band */}
        <rect x="8" y="56" width="36" height="4" rx="1" fill="#1B3D6E"/>
    </svg>
);

/* ─── GovHeader ─────────────────────────────────────── */
const GovHeader = ({ showNav = true, backHref = null, backLabel = null }) => {
    const { language } = useLanguage();

    return (
        <header role="banner" style={{ width: '100%', fontFamily: "'Noto Sans', 'Noto Sans Devanagari', sans-serif" }}>

            {/* Skip to main content (accessibility) */}
            <a href="#main-content" style={{
                position: 'absolute', left: -9999, top: 4, zIndex: 999,
                background: '#1B3D6E', color: 'white', padding: '6px 12px', fontSize: 13, fontWeight: 700,
                borderRadius: 4,
                ':focus': { left: 4 }
            }} onFocus={e => e.target.style.left = '4px'} onBlur={e => e.target.style.left = '-9999px'}>
                Skip to main content
            </a>

            {/* ── Tricolour strip ── */}
            <div style={{ display: 'flex', height: 6 }} aria-hidden="true">
                <div style={{ flex: 1, background: '#FF9933' }} />
                <div style={{ flex: 1, background: '#FFFFFF' }} />
                <div style={{ flex: 1, background: '#138808' }} />
            </div>

            {/* ── Top government bar ── */}
            <div style={{
                background: '#FFFFFF',
                borderBottom: '1px solid #D5D5D5',
                padding: '10px 20px',
                display: 'flex',
                alignItems: 'center',
                gap: 16
            }}>
                <AshokaEmblem />
                <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, color: '#555', fontWeight: 600, letterSpacing: 0.3 }}>
                        भारत सरकार | Government of India
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 900, color: '#1B3D6E', lineHeight: 1.2, marginTop: 2 }}>
                        Zelia — कल्याण योजना पोर्टल
                    </div>
                    <div style={{ fontSize: 12, color: '#444', fontWeight: 600, letterSpacing: 0.2 }}>
                        Welfare Scheme Access Portal
                    </div>
                </div>
                {/* NIC / Digital India badges */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                    <div style={{ fontSize: 10, color: '#888', fontWeight: 600, letterSpacing: 0.3 }}>Powered by</div>
                    <div style={{ display: 'flex', gap: 6 }}>
                        <span style={{ fontSize: 10, background: '#1B3D6E', color: 'white', padding: '2px 7px', borderRadius: 3, fontWeight: 700, letterSpacing: 0.5 }}>NIC</span>
                        <span style={{ fontSize: 10, background: '#138808', color: 'white', padding: '2px 7px', borderRadius: 3, fontWeight: 700, letterSpacing: 0.5 }}>DigiIndia</span>
                    </div>
                </div>
            </div>

            {/* ── Navy nav bar ── */}
            {showNav && (
                <div style={{
                    background: '#1B3D6E',
                    padding: '8px 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 12,
                    flexWrap: 'wrap'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        {backHref && (
                            <a href={backHref} style={{
                                color: 'rgba(255,255,255,.85)', fontSize: 13, fontWeight: 700,
                                display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none'
                            }}>
                                ‹ {backLabel || 'Back'}
                            </a>
                        )}
                        <a href="/citizen" style={{ color: 'rgba(255,255,255,.7)', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
                            Home
                        </a>
                        <a href="/citizen/documents" style={{ color: 'rgba(255,255,255,.7)', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
                            {language === 'Hindi' ? 'दस्तावेज़ वॉल्ट' : 'Document Vault'}
                        </a>
                        <a href="/eligibility" style={{ color: 'rgba(255,255,255,.7)', fontSize: 13, fontWeight: 600, textDecoration: 'none' }}>
                            {language === 'Hindi' ? 'पात्रता जाँच' : 'Eligibility Check'}
                        </a>
                    </div>
                    <LanguagePicker dark />
                </div>
            )}

            {/* ── Important notice bar ── */}
            <div style={{
                background: '#FFF8E1',
                borderBottom: '1px solid #FFE082',
                padding: '5px 20px',
                fontSize: 11,
                color: '#6D4C00',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6
            }}>
                <span style={{ fontSize: 14 }}>🔒</span>
                This is an official Government of India website. All data is encrypted and protected.
                &nbsp;|&nbsp; यह भारत सरकार की आधिकारिक वेबसाइट है।
            </div>
        </header>
    );
};

/* ─── GovFooter ─────────────────────────────────────── */
export const GovFooter = () => (
    <footer style={{
        background: '#1B3D6E',
        color: 'rgba(255,255,255,.75)',
        padding: '20px',
        marginTop: 'auto',
        fontFamily: "'Noto Sans', sans-serif"
    }}>
        <div style={{ maxWidth: 680, margin: '0 auto' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, justifyContent: 'space-between', marginBottom: 16 }}>
                <div>
                    <div style={{ color: 'white', fontWeight: 800, fontSize: 13, marginBottom: 6 }}>Quick Links</div>
                    {[
                        ['MyScheme Portal', 'https://myscheme.gov.in'],
                        ['DigiLocker', 'https://digilocker.gov.in'],
                        ['Jan Samarth', 'https://jansamarth.in'],
                        ['UMANG', 'https://web.umang.gov.in']
                    ].map(([label, href]) => (
                        <a key={label} href={href} target="_blank" rel="noreferrer"
                            style={{ display: 'block', color: 'rgba(255,255,255,.65)', fontSize: 12, fontWeight: 600, marginBottom: 3, textDecoration: 'none' }}>
                            {label} ↗
                        </a>
                    ))}
                </div>
                <div>
                    <div style={{ color: 'white', fontWeight: 800, fontSize: 13, marginBottom: 6 }}>Contact</div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,.65)', lineHeight: 1.8 }}>
                        Helpline: 1800-XXX-XXXX (Toll Free)<br />
                        Email: support@zelia.gov.in<br />
                        Mon – Sat | 9 AM – 6 PM IST
                    </div>
                </div>
                <div>
                    <div style={{ color: 'white', fontWeight: 800, fontSize: 13, marginBottom: 6 }}>Accessibility</div>
                    <div style={{ fontSize: 12, color: 'rgba(255,255,255,.65)', lineHeight: 1.8 }}>
                        Screen Reader Compatible<br />
                        WCAG 2.1 AA Compliant<br />
                        Available in 4 languages
                    </div>
                </div>
            </div>
            <div style={{ borderTop: '1px solid rgba(255,255,255,.15)', paddingTop: 12, fontSize: 11, color: 'rgba(255,255,255,.5)', lineHeight: 1.6 }}>
                © 2024 Ministry of Rural Development, Government of India. Content on this website is published and managed by NIC.
                &nbsp;|&nbsp; Disclaimer &nbsp;|&nbsp; Privacy Policy &nbsp;|&nbsp; Terms of Use &nbsp;|&nbsp; Website Policies
            </div>
        </div>
    </footer>
);

export default GovHeader;
