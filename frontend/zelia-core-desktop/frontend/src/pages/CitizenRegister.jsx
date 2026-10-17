import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Camera, UploadCloud, CheckCircle, ChevronLeft, ChevronRight, User, AlertCircle } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import GovHeader, { GovFooter } from '../components/GovHeader';

const CitizenRegister = () => {
    const navigate = useNavigate();
    const { language } = useLanguage();

    // Steps: 0: Welcome, 1: Consent, 2: Document Upload
    const [step, setStep] = useState(0);
    const [ocrLoading, setOcrLoading] = useState(false);
    const [uploadSuccess, setUploadSuccess] = useState(false);
    const [consentChecked, setConsentChecked] = useState(false);
    const ocrInputRef = useRef(null);

    const STEPS_EN = ['Welcome', 'Consent', 'Upload ID'];
    const STEPS_HI = ['स्वागत', 'सहमति', 'ID अपलोड'];
    const steps = language === 'Hindi' ? STEPS_HI : STEPS_EN;

    const handleOcrUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setOcrLoading(true);
        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('document_type', 'aadhaar');

            let userId = localStorage.getItem('zelia_user_id');
            if (!userId) {
                userId = 'citizen-' + Math.floor(Math.random() * 10000);
                localStorage.setItem('zelia_user_id', userId);
            }
            formData.append('user_id', userId);

            const response = await fetch('http://localhost:8009/sync', { method: 'POST', body: formData });

            if (!response.ok) throw new Error('Submission API Failed');

            const result = await response.json();
            if (result.submission_id) {
                localStorage.setItem('zelia_submission_id', result.submission_id);
                setUploadSuccess(true);
                setTimeout(() => navigate('/citizen-login'), 3000);
            } else {
                alert(language === 'Hindi'
                    ? 'दस्तावेज़ प्रोसेस नहीं हो सका। स्पष्ट फ़ोटो लेकर पुनः प्रयास करें।'
                    : 'Could not process document. Please try a clearer photo.');
            }
        } catch {
            alert(language === 'Hindi'
                ? 'सेवा उपलब्ध नहीं है। बाद में पुनः प्रयास करें।'
                : 'Service unavailable. Try again later.');
        } finally {
            setOcrLoading(false);
        }
    };

    return (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#EEF2F7', fontFamily: "'Noto Sans','Noto Sans Devanagari',sans-serif" }}>
            <GovHeader showNav={false} />

            <main id="main-content" style={{ flex: 1, maxWidth: 560, width: '100%', margin: '0 auto', padding: '28px 16px 48px' }}>

                {/* Breadcrumb */}
                <div style={{ fontSize: 12, color: '#555', marginBottom: 18 }}>
                    <a href="/" style={{ color: '#1B3D6E', textDecoration: 'none', fontWeight: 600 }}>Home</a>
                    <span style={{ margin: '0 6px', color: '#999' }}>›</span>
                    <a href="/citizen-login" style={{ color: '#1B3D6E', textDecoration: 'none', fontWeight: 600 }}>
                        {language === 'Hindi' ? 'लॉगिन' : 'Login'}
                    </a>
                    <span style={{ margin: '0 6px', color: '#999' }}>›</span>
                    <span style={{ fontWeight: 700, color: '#333' }}>
                        {language === 'Hindi' ? 'नया पंजीकरण' : 'New Registration'}
                    </span>
                </div>

                {/* Page heading */}
                <div style={{ marginBottom: 22 }}>
                    <h1 style={{ fontSize: 22, fontWeight: 900, color: '#1B3D6E', margin: '0 0 4px' }}>
                        {language === 'Hindi' ? 'नागरिक पंजीकरण' : 'Citizen Registration'}
                    </h1>
                    <p style={{ color: '#555', fontSize: 13, margin: 0 }}>
                        {language === 'Hindi'
                            ? 'कल्याण योजनाओं तक पहुँच के लिए पंजीकरण करें — भारत सरकार'
                            : 'Register to access Government of India welfare schemes'}
                    </p>
                </div>

                {/* Step progress bar */}
                <div style={{ display: 'flex', marginBottom: 24, background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden' }}>
                    {steps.map((s, i) => (
                        <div key={s} style={{
                            flex: 1, padding: '10px 8px', textAlign: 'center', fontSize: 12, fontWeight: 700,
                            background: i < step ? '#E8F5E9' : i === step ? '#1B3D6E' : 'white',
                            color: i < step ? '#1B5E20' : i === step ? 'white' : '#888',
                            borderRight: i < steps.length - 1 ? '1px solid #D8E0EA' : 'none',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5
                        }}>
                            <span style={{
                                display: 'inline-flex', width: 18, height: 18, borderRadius: '50%',
                                background: i < step ? '#138808' : i === step ? 'rgba(255,255,255,.25)' : '#DDD',
                                color: i < step ? 'white' : i === step ? 'white' : '#888',
                                fontSize: 10, fontWeight: 900, alignItems: 'center', justifyContent: 'center'
                            }}>
                                {i < step ? '✓' : i + 1}
                            </span>
                            {s}
                        </div>
                    ))}
                </div>

                {/* Step 0: Welcome */}
                {step === 0 && (
                    <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ background: '#1B3D6E', padding: '11px 18px' }}>
                            <span style={{ color: 'white', fontWeight: 800, fontSize: 13, letterSpacing: 0.4 }}>
                                {language === 'Hindi' ? 'पोर्टल में आपका स्वागत है' : 'WELCOME TO THE PORTAL'}
                            </span>
                        </div>
                        <div style={{ padding: '24px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 16, marginBottom: 28 }}>
                                <div style={{ width: 80, height: 80, borderRadius: '50%', background: '#EEF2F7', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <User size={40} color="#1B3D6E" />
                                </div>
                                <div>
                                    <h2 style={{ fontSize: 20, fontWeight: 900, color: '#1B3D6E', margin: '0 0 8px' }}>
                                        Zelia — {language === 'Hindi' ? 'कल्याण योजना पोर्टल' : 'Welfare Scheme Portal'}
                                    </h2>
                                    <p style={{ fontSize: 13, color: '#555', lineHeight: 1.7, margin: 0, maxWidth: 380 }}>
                                        {language === 'Hindi'
                                            ? 'यह AI-संचालित पोर्टल आपको सरकारी कल्याण योजनाओं तक पहुँचने में मदद करता है। पंजीकरण के लिए आगे बढ़ें।'
                                            : 'This AI-powered portal helps you access Government of India welfare schemes. Register to check your eligibility via voice interview.'}
                                    </p>
                                </div>
                            </div>

                            {/* Feature list */}
                            <div style={{ marginBottom: 24 }}>
                                {[
                                    { icon: '🎙️', en: 'Voice eligibility interview in your language', hi: 'आपकी भाषा में वॉइस पात्रता इंटरव्यू' },
                                    { icon: '📄', en: 'Automatic government form filling', hi: 'स्वचालित सरकारी फॉर्म भरना' },
                                    { icon: '🔒', en: 'Secure encrypted document vault', hi: 'सुरक्षित एन्क्रिप्टेड दस्तावेज़ वॉल्ट' },
                                    { icon: '🏛️', en: 'Access PM-JAY, NREGA, PM Awas & more', hi: 'PM-JAY, नरेगा, PM आवास और अधिक' },
                                ].map(f => (
                                    <div key={f.en} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid #EEF2F7', fontSize: 13 }}>
                                        <span style={{ fontSize: 18, flexShrink: 0 }}>{f.icon}</span>
                                        <span style={{ color: '#444', fontWeight: 600 }}>{language === 'Hindi' ? f.hi : f.en}</span>
                                    </div>
                                ))}
                            </div>

                            <button onClick={() => setStep(1)} style={{ width: '100%', padding: '13px', borderRadius: 3, border: 'none', background: '#1B3D6E', color: 'white', fontSize: 15, fontWeight: 900, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, fontFamily: 'inherit' }}
                                onMouseOver={e => e.currentTarget.style.background = '#142d52'}
                                onMouseOut={e => e.currentTarget.style.background = '#1B3D6E'}>
                                {language === 'Hindi' ? 'आगे बढ़ें' : 'Get Started'} <ChevronRight size={16} />
                            </button>
                            <div style={{ marginTop: 12, textAlign: 'center' }}>
                                <a href="/citizen-login" style={{ fontSize: 13, color: '#1B3D6E', fontWeight: 700, textDecoration: 'none' }}>
                                    {language === 'Hindi' ? 'पहले से पंजीकृत? लॉगिन करें' : 'Already registered? Login →'}
                                </a>
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 1: Consent */}
                {step === 1 && (
                    <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ background: '#1B3D6E', padding: '11px 18px' }}>
                            <span style={{ color: 'white', fontWeight: 800, fontSize: 13, letterSpacing: 0.4 }}>
                                {language === 'Hindi' ? 'डेटा सहमति और गोपनीयता नीति' : 'DATA CONSENT & PRIVACY POLICY'}
                            </span>
                        </div>
                        <div style={{ padding: '24px' }}>
                            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
                                <Shield size={52} color="#1B3D6E" />
                            </div>

                            <div style={{ background: '#F0F4FA', border: '1px solid #D0DBE8', borderRadius: 3, padding: 16, marginBottom: 20, maxHeight: 220, overflowY: 'auto', fontSize: 13, color: '#444', lineHeight: 1.8 }}>
                                <p style={{ fontWeight: 800, color: '#1B3D6E', marginBottom: 8 }}>
                                    {language === 'Hindi' ? 'डेटा उपयोग की शर्तें:' : 'Terms of Data Usage:'}
                                </p>
                                <ul style={{ paddingLeft: 18, margin: 0 }}>
                                    {[
                                        ['Your personal data will be used solely to match you with eligible government welfare schemes.',
                                            'आपका व्यक्तिगत डेटा केवल सरकारी कल्याण योजनाओं से मिलान के लिए उपयोग किया जाएगा।'],
                                        ['Documents uploaded are stored encrypted under your unique household ID.',
                                            'अपलोड किए गए दस्तावेज़ आपकी विशिष्ट घरेलू ID के तहत एन्क्रिप्टेड रूप में संग्रहीत हैं।'],
                                        ['Aadhaar number is hashed (SHA-256) client-side and never transmitted in plain text.',
                                            'आधार नंबर SHA-256 से हैश किया जाता है और कभी स्पष्ट टेक्स्ट में संचारित नहीं होता।'],
                                        ['Voice interview transcripts are processed by AI for eligibility determination only.',
                                            'वॉइस इंटरव्यू ट्रांसक्रिप्ट केवल पात्रता निर्धारण के लिए AI द्वारा संसाधित की जाती है।'],
                                        ['You may request data deletion at any time via the Helpline.',
                                            'आप किसी भी समय हेल्पलाइन के माध्यम से डेटा हटाने का अनुरोध कर सकते हैं।'],
                                    ].map(([en, hi]) => (
                                        <li key={en} style={{ marginBottom: 6 }}>{language === 'Hindi' ? hi : en}</li>
                                    ))}
                                </ul>
                            </div>

                            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, cursor: 'pointer', marginBottom: 20 }}>
                                <input type="checkbox" checked={consentChecked} onChange={e => setConsentChecked(e.target.checked)}
                                    style={{ width: 18, height: 18, marginTop: 2, cursor: 'pointer', flexShrink: 0 }} />
                                <span style={{ fontSize: 13, color: '#333', lineHeight: 1.6, fontWeight: 600 }}>
                                    {language === 'Hindi'
                                        ? 'मैं उपरोक्त डेटा उपयोग नीति से सहमत हूँ और भारत सरकार के कल्याण योजना पोर्टल पर पंजीकरण करने की सहमति देता/देती हूँ।'
                                        : 'I agree to the above data usage policy and consent to register on the Government of India Welfare Scheme Portal.'}
                                </span>
                            </label>

                            {!consentChecked && (
                                <div style={{ background: '#FFF8E1', border: '1px solid #FFE082', borderRadius: 3, padding: '8px 12px', marginBottom: 16, fontSize: 12, color: '#5D4037', display: 'flex', gap: 8, alignItems: 'center' }}>
                                    <AlertCircle size={13} /> {language === 'Hindi' ? 'कृपया आगे बढ़ने के लिए सहमत हों।' : 'Please agree to the terms to proceed.'}
                                </div>
                            )}

                            <div style={{ display: 'flex', gap: 10 }}>
                                <button onClick={() => setStep(0)} style={{ flex: 1, padding: '12px', borderRadius: 3, border: '1.5px solid #CCC', background: 'white', color: '#333', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                                    <ChevronLeft size={14} style={{ verticalAlign: 'middle' }} /> {language === 'Hindi' ? 'वापस' : 'Back'}
                                </button>
                                <button onClick={() => setStep(2)} disabled={!consentChecked}
                                    style={{ flex: 2, padding: '12px', borderRadius: 3, border: 'none', background: consentChecked ? '#138808' : '#B0BEC5', color: 'white', fontSize: 14, fontWeight: 800, cursor: consentChecked ? 'pointer' : 'not-allowed', fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                                    <CheckCircle size={15} /> {language === 'Hindi' ? 'मैं सहमत हूँ — आगे बढ़ें' : 'I Agree — Continue'} <ChevronRight size={14} />
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 2: Upload ID */}
                {step === 2 && (
                    <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden' }}>
                        <div style={{ background: '#FF9933', padding: '11px 18px' }}>
                            <span style={{ color: 'white', fontWeight: 800, fontSize: 13, letterSpacing: 0.4 }}>
                                {language === 'Hindi' ? 'पहचान दस्तावेज़ अपलोड करें' : 'UPLOAD IDENTITY DOCUMENT'}
                            </span>
                        </div>
                        <div style={{ padding: '24px' }}>
                            {uploadSuccess ? (
                                <div style={{ textAlign: 'center', padding: '20px 0' }}>
                                    <div style={{ width: 80, height: 80, borderRadius: '50%', background: '#E8F5E9', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                                        <CheckCircle size={44} color="#138808" />
                                    </div>
                                    <h2 style={{ fontSize: 20, fontWeight: 900, color: '#1B5E20', marginBottom: 8 }}>
                                        {language === 'Hindi' ? 'पंजीकरण सफल!' : 'Registration Successful!'}
                                    </h2>
                                    <p style={{ fontSize: 14, color: '#555', marginBottom: 6 }}>
                                        {language === 'Hindi' ? 'आपकी पहचान सत्यापित की जा रही है। लॉगिन पर रीडायरेक्ट हो रहे हैं…' : 'Your identity is being verified. Redirecting to login…'}
                                    </p>
                                    <div style={{ fontSize: 12, color: '#888' }}>Please note your registration ID for future reference.</div>
                                </div>
                            ) : (
                                <>
                                    <p style={{ fontSize: 13, color: '#555', lineHeight: 1.7, marginBottom: 20, borderLeft: '3px solid #FF9933', paddingLeft: 10 }}>
                                        {language === 'Hindi'
                                            ? 'अपना आधार कार्ड, पैन कार्ड, या मतदाता पहचान पत्र अपलोड करें। हमारा OCR सिस्टम आपके विवरण स्वचालित रूप से निकाल लेगा।'
                                            : 'Upload your Aadhaar Card, PAN Card, or Voter ID. Our OCR system will automatically extract your details.'}
                                    </p>

                                    {/* Accepted document types */}
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
                                        {[
                                            ['🪪', 'Aadhaar Card', 'आधार कार्ड'],
                                            ['💳', 'PAN Card', 'PAN कार्ड'],
                                            ['🗳️', 'Voter ID', 'मतदाता पहचान'],
                                            ['📘', 'Ration Card', 'राशन कार्ड'],
                                        ].map(([icon, en, hi]) => (
                                            <div key={en} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 10px', background: '#F0F4FA', border: '1px solid #D0DBE8', borderRadius: 3, fontSize: 12, fontWeight: 700, color: '#1B3D6E' }}>
                                                {icon} {language === 'Hindi' ? hi : en}
                                            </div>
                                        ))}
                                    </div>

                                    <input type="file" ref={ocrInputRef} onChange={handleOcrUpload} accept="image/*,.pdf" style={{ display: 'none' }} />

                                    {/* Upload area */}
                                    <div onClick={() => ocrInputRef.current?.click()}
                                        style={{ border: '2px dashed #9BAFC7', borderRadius: 4, padding: '32px 20px', textAlign: 'center', cursor: 'pointer', marginBottom: 20, background: '#F8FAFD', transition: 'all .15s' }}
                                        onMouseOver={e => { e.currentTarget.style.borderColor = '#1B3D6E'; e.currentTarget.style.background = '#EEF2F7'; }}
                                        onMouseOut={e => { e.currentTarget.style.borderColor = '#9BAFC7'; e.currentTarget.style.background = '#F8FAFD'; }}>
                                        {ocrLoading ? (
                                            <>
                                                <div style={{ width: 48, height: 48, borderRadius: '50%', border: '4px solid #EEF2F7', borderTop: '4px solid #1B3D6E', animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
                                                <div style={{ fontSize: 14, fontWeight: 700, color: '#1B3D6E' }}>
                                                    {language === 'Hindi' ? 'दस्तावेज़ प्रोसेस हो रहा है…' : 'Processing document…'}
                                                </div>
                                                <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>OCR extraction in progress</div>
                                            </>
                                        ) : (
                                            <>
                                                <Camera size={40} color="#9BAFC7" style={{ marginBottom: 12 }} />
                                                <div style={{ fontSize: 15, fontWeight: 800, color: '#1B3D6E', marginBottom: 4 }}>
                                                    {language === 'Hindi' ? 'फ़ाइल चुनें या यहाँ खींचें' : 'Choose file or drag here'}
                                                </div>
                                                <div style={{ fontSize: 12, color: '#888' }}>
                                                    {language === 'Hindi' ? 'JPG, PNG या PDF — अधिकतम 5MB' : 'JPG, PNG or PDF — max 5MB'}
                                                </div>
                                                <div style={{ marginTop: 12, display: 'inline-block', padding: '8px 20px', borderRadius: 3, background: '#1B3D6E', color: 'white', fontSize: 13, fontWeight: 800 }}>
                                                    <UploadCloud size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
                                                    {language === 'Hindi' ? 'फ़ाइल चुनें' : 'Choose File'}
                                                </div>
                                            </>
                                        )}
                                    </div>

                                    <div style={{ display: 'flex', gap: 10 }}>
                                        <button onClick={() => setStep(1)} style={{ flex: 1, padding: '12px', borderRadius: 3, border: '1.5px solid #CCC', background: 'white', color: '#333', fontSize: 14, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit' }}>
                                            <ChevronLeft size={14} style={{ verticalAlign: 'middle' }} /> {language === 'Hindi' ? 'वापस' : 'Back'}
                                        </button>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                )}

                {/* Already have account */}
                {!uploadSuccess && (
                    <div style={{ marginTop: 16, textAlign: 'center', fontSize: 13, color: '#666' }}>
                        {language === 'Hindi' ? 'पहले से पंजीकृत?' : 'Already have an account?'}
                        &nbsp;<a href="/citizen-login" style={{ color: '#1B3D6E', fontWeight: 800, textDecoration: 'none' }}>
                            {language === 'Hindi' ? 'लॉगिन करें →' : 'Login →'}
                        </a>
                    </div>
                )}

                <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
            </main>

            <GovFooter />
        </div>
    );
};

export default CitizenRegister;
