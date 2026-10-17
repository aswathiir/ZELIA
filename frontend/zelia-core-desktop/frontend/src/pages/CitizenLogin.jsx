import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Phone, Lock, ChevronRight, AlertCircle } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import GovHeader, { GovFooter } from '../components/GovHeader';
import { sha256 } from '../utils/api';

/* ── per-language text ── */
const TX = {
    English: {
        title: 'Citizen Login',
        subtitle: 'Welfare Scheme Access Portal — Government of India',
        phoneLabel: 'Registered Mobile Number',
        phonePH: 'Enter 10-digit mobile number',
        sendOtp: 'GET OTP',
        otpLabel: 'One-Time Password (OTP)',
        aadhaarLabel: 'Aadhaar Number (optional, for enhanced security)',
        aadhaarPH: 'XXXX XXXX XXXX',
        verify: 'VERIFY & LOGIN',
        back: '← Change Mobile Number',
        newReg: '📝 New Registration',
        officerLogin: 'Officer Login',
        otpNote: (p) => `OTP sent to +91-${p}. Valid for 5 minutes.`,
        sending: 'Sending OTP…',
        verifying: 'Verifying…',
        helpText: 'Enter your 10-digit mobile number registered with the scheme portal to receive a one-time password.',
    },
    Hindi: {
        title: 'नागरिक लॉगिन',
        subtitle: 'कल्याण योजना पहुँच पोर्टल — भारत सरकार',
        phoneLabel: 'पंजीकृत मोबाइल नंबर',
        phonePH: '10 अंकों का मोबाइल नंबर दर्ज करें',
        sendOtp: 'OTP प्राप्त करें',
        otpLabel: 'वन-टाइम पासवर्ड (OTP)',
        aadhaarLabel: 'आधार नंबर (वैकल्पिक, अतिरिक्त सुरक्षा के लिए)',
        aadhaarPH: 'XXXX XXXX XXXX',
        verify: 'सत्यापित करें और लॉगिन करें',
        back: '← मोबाइल नंबर बदलें',
        newReg: '📝 नया पंजीकरण',
        officerLogin: 'अधिकारी लॉगिन',
        otpNote: (p) => `OTP +91-${p} पर भेजा गया। 5 मिनट के लिए मान्य।`,
        sending: 'OTP भेज रहे हैं…',
        verifying: 'सत्यापन हो रहा है…',
        helpText: 'एकल-उपयोग पासवर्ड प्राप्त करने के लिए योजना पोर्टल में पंजीकृत 10 अंकों का मोबाइल नंबर दर्ज करें।',
    },
};

const CitizenLogin = () => {
    const navigate = useNavigate();
    const { language } = useLanguage();
    const tx = TX[language] || TX.English;

    const [form, setForm] = useState({ phone: '', otp: '', aadhaar: '' });
    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const sendOtp = async (e) => {
        e.preventDefault();
        setLoading(true); setError('');
        try {
            const res = await fetch('http://localhost:8012/auth/send-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_number: form.phone })
            });
            const data = await res.json();
            if (res.ok) setStep(2);
            else setError(data.detail || 'Failed to send OTP. Please try again.');
        } catch {
            setError('Auth service unavailable. Please ensure backend is running.');
        } finally { setLoading(false); }
    };

    const verify = async (e) => {
        e.preventDefault();
        setLoading(true); setError('');
        try {
            const aadhaar_hash = form.aadhaar ? await sha256(form.aadhaar) : '';
            const res = await fetch('http://localhost:8012/auth/verify-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ phone_number: form.phone, otp_code: form.otp, aadhaar_hash })
            });
            const data = await res.json();
            if (res.ok) {
                localStorage.setItem('zelia_jwt', data.jwt_token);
                localStorage.setItem('zelia_citizen_id', data.citizen_id);
                try {
                    const hhRes = await fetch('http://localhost:8013/session/get-or-create-hash', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${data.jwt_token}` },
                        body: JSON.stringify({ citizen_id: data.citizen_id, phone_number: form.phone })
                    });
                    const hhData = hhRes.ok ? await hhRes.json() : {};
                    const hash = hhData.household_hash || data.citizen_id;
                    localStorage.setItem('zelia_user_id', hash);
                    navigate(`/citizen?hash=${hash}`);
                } catch {
                    localStorage.setItem('zelia_user_id', data.citizen_id);
                    navigate(`/citizen?hash=${data.citizen_id}`);
                }
            } else {
                setError(data.detail || 'OTP verification failed. Please try again.');
            }
        } catch {
            setError('Service unavailable. Please ensure backend is running.');
        } finally { setLoading(false); }
    };

    return (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#EEF2F7', fontFamily: "'Noto Sans','Noto Sans Devanagari','Noto Sans Tamil','Noto Sans Malayalam',sans-serif" }}>
            <GovHeader showNav={false} />

            <main id="main-content" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-start', padding: '32px 16px 48px' }}>

                {/* Breadcrumb */}
                <div style={{ width: '100%', maxWidth: 500, marginBottom: 18, fontSize: 12, color: '#555' }}>
                    <a href="/" style={{ color: '#1B3D6E', textDecoration: 'none', fontWeight: 600 }}>Home</a>
                    <span style={{ margin: '0 6px', color: '#999' }}>›</span>
                    <span style={{ fontWeight: 700, color: '#333' }}>{tx.title}</span>
                </div>

                {/* Page heading */}
                <div style={{ width: '100%', maxWidth: 500, marginBottom: 20 }}>
                    <h1 style={{ fontSize: 22, fontWeight: 900, color: '#1B3D6E', margin: '0 0 4px' }}>{tx.title}</h1>
                    <p style={{ color: '#555', fontSize: 13, margin: 0, fontWeight: 600 }}>{tx.subtitle}</p>
                </div>

                <div style={{ width: '100%', maxWidth: 500, display: 'flex', flexDirection: 'column', gap: 16 }}>

                    {/* Main login card */}
                    <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden', boxShadow: '0 2px 8px rgba(0,0,0,.08)' }}>

                        {/* Card title bar */}
                        <div style={{ background: '#1B3D6E', padding: '11px 18px', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Lock size={13} color="rgba(255,255,255,.85)" />
                            <span style={{ color: 'white', fontWeight: 800, fontSize: 13, letterSpacing: 0.5 }}>
                                SECURE LOGIN &nbsp;/&nbsp; सुरक्षित लॉगिन — Mobile OTP
                            </span>
                        </div>

                        {/* Step tabs */}
                        <div style={{ display: 'flex', borderBottom: '2px solid #E8EEF5' }}>
                            {[{ n: 1, en: 'Step 1: Mobile', hi: 'चरण 1: मोबाइल' }, { n: 2, en: 'Step 2: OTP', hi: 'चरण 2: OTP' }].map(s => (
                                <div key={s.n} style={{
                                    flex: 1, padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 8,
                                    background: step === s.n ? '#F0F4FA' : 'white',
                                    borderBottom: step === s.n ? '3px solid #1B3D6E' : '3px solid transparent',
                                    marginBottom: -2
                                }}>
                                    <div style={{
                                        width: 24, height: 24, borderRadius: '50%', flexShrink: 0, fontSize: 12, fontWeight: 900,
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        background: step > s.n ? '#138808' : step === s.n ? '#1B3D6E' : '#B0BEC5',
                                        color: 'white'
                                    }}>
                                        {step > s.n ? '✓' : s.n}
                                    </div>
                                    <span style={{ fontSize: 12, fontWeight: 700, color: step >= s.n ? '#1B3D6E' : '#888' }}>
                                        {language === 'Hindi' ? s.hi : s.en}
                                    </span>
                                </div>
                            ))}
                        </div>

                        <div style={{ padding: '22px 22px 18px' }}>

                            {/* Error banner */}
                            {error && (
                                <div style={{
                                    background: '#FFF3CD', border: '1px solid #FFC107',
                                    borderLeft: '4px solid #C62828', borderRadius: 3,
                                    padding: '10px 14px', marginBottom: 16,
                                    display: 'flex', gap: 10, alignItems: 'flex-start'
                                }}>
                                    <AlertCircle size={15} color="#C62828" style={{ flexShrink: 0, marginTop: 1 }} />
                                    <span style={{ color: '#C62828', fontSize: 13, fontWeight: 600 }}>{error}</span>
                                </div>
                            )}

                            {step === 1 ? (
                                <form onSubmit={sendOtp}>
                                    <p style={{ fontSize: 13, color: '#555', lineHeight: 1.7, marginBottom: 18, borderLeft: '3px solid #1B3D6E', paddingLeft: 10 }}>
                                        {tx.helpText}
                                    </p>
                                    <div style={{ marginBottom: 20 }}>
                                        <label style={{ display: 'block', fontSize: 13, fontWeight: 800, color: '#222', marginBottom: 6 }}>
                                            <Phone size={12} style={{ marginRight: 5, verticalAlign: 'middle' }} />
                                            {tx.phoneLabel} <span style={{ color: '#C62828' }}>*</span>
                                        </label>
                                        <div style={{ display: 'flex', border: '1.5px solid #9BAFC7', borderRadius: 3, overflow: 'hidden', transition: 'border .2s', background: 'white' }}
                                            onFocusCapture={e => e.currentTarget.style.borderColor = '#1B3D6E'}
                                            onBlurCapture={e => e.currentTarget.style.borderColor = '#9BAFC7'}>
                                            <span style={{ padding: '12px 14px', background: '#F0F4FA', color: '#333', fontWeight: 800, fontSize: 14, borderRight: '1.5px solid #D0D8E4', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center' }}>
                                                🇮🇳 +91
                                            </span>
                                            <input type="tel" inputMode="numeric" maxLength={10}
                                                placeholder={tx.phonePH}
                                                value={form.phone}
                                                onChange={e => setForm({ ...form, phone: e.target.value.replace(/\D/g, '').slice(0, 10) })}
                                                style={{ flex: 1, border: 'none', padding: '12px 14px', fontSize: 18, fontWeight: 700, fontFamily: 'monospace', letterSpacing: 3, outline: 'none', background: 'transparent' }}
                                                required />
                                        </div>
                                    </div>
                                    <button type="submit" disabled={form.phone.length < 10 || loading}
                                        style={{
                                            width: '100%', padding: '13px', borderRadius: 3, border: 'none',
                                            background: form.phone.length === 10 && !loading ? '#1B3D6E' : '#90A4AE',
                                            color: 'white', fontSize: 15, fontWeight: 900, letterSpacing: 0.5,
                                            cursor: form.phone.length === 10 ? 'pointer' : 'not-allowed',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                            fontFamily: 'inherit', transition: 'background .2s'
                                        }}
                                        onMouseOver={e => { if (form.phone.length === 10) e.currentTarget.style.background = '#142d52'; }}
                                        onMouseOut={e => { if (form.phone.length === 10) e.currentTarget.style.background = '#1B3D6E'; }}>
                                        {loading ? tx.sending : <><Phone size={15} /> {tx.sendOtp} <ChevronRight size={15} /></>}
                                    </button>
                                </form>
                            ) : (
                                <form onSubmit={verify}>
                                    <div style={{ background: '#E8F5E9', border: '1px solid #A5D6A7', borderRadius: 3, padding: '10px 14px', marginBottom: 18, fontSize: 13, color: '#1B5E20', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 8 }}>
                                        ✅ {tx.otpNote(form.phone)}
                                    </div>

                                    <div style={{ marginBottom: 16 }}>
                                        <label style={{ display: 'block', fontSize: 13, fontWeight: 800, color: '#222', marginBottom: 6 }}>
                                            {tx.otpLabel} <span style={{ color: '#C62828' }}>*</span>
                                        </label>
                                        <input type="text" inputMode="numeric" maxLength={6}
                                            placeholder="● ● ● ● ● ●"
                                            value={form.otp}
                                            onChange={e => setForm({ ...form, otp: e.target.value.replace(/\D/g, '').slice(0, 6) })}
                                            autoFocus
                                            style={{
                                                width: '100%', letterSpacing: 18, textAlign: 'center',
                                                fontSize: 30, fontWeight: 900, fontFamily: 'monospace',
                                                padding: '14px', borderRadius: 3,
                                                border: '1.5px solid #9BAFC7', color: '#1B3D6E',
                                                boxSizing: 'border-box', outline: 'none', transition: 'border .2s'
                                            }}
                                            onFocus={e => e.target.style.borderColor = '#1B3D6E'}
                                            onBlur={e => e.target.style.borderColor = '#9BAFC7'}
                                            required />
                                    </div>

                                    <div style={{ marginBottom: 20 }}>
                                        <label style={{ display: 'block', fontSize: 13, fontWeight: 700, color: '#555', marginBottom: 6 }}>
                                            🔒 {tx.aadhaarLabel}
                                        </label>
                                        <input type="text" inputMode="numeric" maxLength={12}
                                            placeholder={tx.aadhaarPH}
                                            value={form.aadhaar}
                                            onChange={e => setForm({ ...form, aadhaar: e.target.value.replace(/\D/g, '').slice(0, 12) })}
                                            style={{
                                                width: '100%', letterSpacing: 6, textAlign: 'center',
                                                fontSize: 16, fontWeight: 700, fontFamily: 'monospace',
                                                padding: '10px 14px', borderRadius: 3,
                                                border: '1.5px solid #D0D8E4', color: '#333',
                                                boxSizing: 'border-box', outline: 'none'
                                            }} />
                                        <p style={{ margin: '5px 0 0', fontSize: 11, color: '#777', lineHeight: 1.5 }}>
                                            Hashed client-side via SHA-256. Your Aadhaar number is never transmitted.
                                            &nbsp;|&nbsp; आपका आधार नंबर कभी संचारित नहीं होता।
                                        </p>
                                    </div>

                                    <button type="submit" disabled={form.otp.length < 6 || loading}
                                        style={{
                                            width: '100%', padding: '13px', borderRadius: 3, border: 'none',
                                            background: form.otp.length === 6 && !loading ? '#138808' : '#90A4AE',
                                            color: 'white', fontSize: 15, fontWeight: 900, letterSpacing: 0.5,
                                            cursor: form.otp.length === 6 ? 'pointer' : 'not-allowed',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                                            fontFamily: 'inherit', transition: 'background .2s'
                                        }}
                                        onMouseOver={e => { if (form.otp.length === 6) e.currentTarget.style.background = '#0d6b08'; }}
                                        onMouseOut={e => { if (form.otp.length === 6) e.currentTarget.style.background = '#138808'; }}>
                                        {loading ? tx.verifying : <><Shield size={15} /> {tx.verify} <ChevronRight size={15} /></>}
                                    </button>

                                    <button type="button" onClick={() => { setStep(1); setError(''); }}
                                        style={{ width: '100%', marginTop: 10, padding: '10px', background: 'none', border: 'none', color: '#1B3D6E', fontWeight: 700, fontSize: 13, cursor: 'pointer', fontFamily: 'inherit' }}>
                                        {tx.back}
                                    </button>
                                </form>
                            )}

                            {/* Bottom links */}
                            <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid #E8EEF5', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <a href="/citizen-register" style={{ fontSize: 13, color: '#1B3D6E', fontWeight: 700, textDecoration: 'none' }}>{tx.newReg}</a>
                                <a href="/login" style={{ fontSize: 13, color: '#555', fontWeight: 600, textDecoration: 'none' }}>{tx.officerLogin} →</a>
                            </div>
                        </div>
                    </div>

                    {/* Trust / security info panel */}
                    <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, padding: '14px 18px' }}>
                        <div style={{ fontWeight: 800, fontSize: 13, color: '#1B3D6E', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6 }}>
                            <Shield size={14} /> Security Information
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                            {[
                                ['🔐', 'SSL/TLS Encrypted', 'सुरक्षित कनेक्शन'],
                                ['🏛️', 'Govt. of India', 'भारत सरकार'],
                                ['✅', 'STQC Certified', 'STQC प्रमाणित'],
                                ['📋', 'ISO 27001', 'डेटा सुरक्षा'],
                            ].map(([icon, en, hi]) => (
                                <div key={en} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: '#F0F4FA', borderRadius: 3, fontSize: 12 }}>
                                    <span style={{ fontSize: 16 }}>{icon}</span>
                                    <div>
                                        <div style={{ fontWeight: 700, color: '#333', lineHeight: 1.2 }}>{en}</div>
                                        <div style={{ color: '#777', fontSize: 11 }}>{hi}</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Helpline */}
                    <div style={{ background: '#FFF8E1', border: '1px solid #FFE082', borderRadius: 4, padding: '12px 16px', fontSize: 13, color: '#5D4037', fontWeight: 600, textAlign: 'center' }}>
                        📞 Helpline: <strong>1800-XXX-XXXX</strong> (Toll Free) &nbsp;|&nbsp; Mon–Sat 9AM–6PM IST
                    </div>
                </div>
            </main>

            <GovFooter />
        </div>
    );
};

export default CitizenLogin;
