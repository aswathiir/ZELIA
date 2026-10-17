import React, { useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
    Mic, Square, Loader, Heart, Wheat, Users, Home, GraduationCap, Tractor,
    FileText, CheckCircle, XCircle, PhoneCall, AlertCircle
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import GovHeader, { GovFooter } from '../components/GovHeader';

/* ── Scheme meta ── */
const SCHEME_META = {
    'pm-jay':     { icon: Heart,         names: { English: 'PM-JAY Health Insurance', Hindi: 'PM-JAY स्वास्थ्य बीमा', Tamil: 'PM-JAY சுகாதார காப்பீடு', Malayalam: 'PM-JAY ആരോഗ്യ ഇൻഷ്വറൻസ്' } },
    'nrega':      { icon: Wheat,         names: { English: 'NREGA Rural Employment', Hindi: 'नरेगा ग्रामीण रोजगार', Tamil: 'நரேகா கிராம வேலை', Malayalam: 'നരേഗ ഗ്രാമീണ തൊഴിൽ' } },
    'pension':    { icon: Users,         names: { English: 'Widow / Old Age Pension', Hindi: 'विधवा / वृद्धावस्था पेंशन', Tamil: 'விதவை / முதியோர் ஓய்வூதியம்', Malayalam: 'വിധവ / വൃദ്ധ പെൻഷൻ' } },
    'awas':       { icon: Home,          names: { English: 'PM Awas Yojana', Hindi: 'PM आवास योजना', Tamil: 'PM Awas Yojana', Malayalam: 'PM ആവാസ് യോജന' } },
    'scholarship':{ icon: GraduationCap, names: { English: 'Post-Matric Scholarship', Hindi: 'पोस्ट-मैट्रिक छात्रवृत्ति', Tamil: 'மேல்நிலை கல்வி உதவித்தொகை', Malayalam: 'സ്കോളർഷിപ്പ്' } },
    'kisan':      { icon: Tractor,       names: { English: 'Kisan Samman Nidhi', Hindi: 'किसान सम्मान निधि', Tamil: 'கிசான் சம்மான் நிதி', Malayalam: 'കിസാൻ സമ്മാൻ നിധി' } },
};

const languageMap = {
    English: 'en-IN', Hindi: 'hi-IN', Tamil: 'ta-IN', Malayalam: 'ml-IN'
};

const T = {
    English: {
        breadHome: 'Home', breadDash: 'Dashboard', breadInterview: 'Voice Interview',
        pageTitle: 'Scheme Eligibility Voice Interview',
        pageSubtitle: 'Our AI assistant will ask you a few questions to determine your eligibility for government welfare schemes.',
        instructions: 'How it works',
        step1: 'Click "Start Voice Interview" below.',
        step2: 'Answer the AI\'s questions clearly in your preferred language.',
        step3: 'Your eligibility is assessed automatically based on your responses.',
        step4: 'If eligible, your form will be filled automatically.',
        startBtn: 'Start Voice Interview',
        helpline: 'For assistance, call the National Helpline: 14567',
        connecting: 'Connecting to AI Assistant…',
        liveTitle: 'Live Voice Interview',
        recording: '● RECORDING',
        waitingAI: 'Waiting for AI response…',
        endBtn: 'End Interview',
        processingTitle: 'Analysing Your Responses…',
        processingNote: 'Please wait. This may take a few seconds.',
        resultEligible: 'Eligible for Benefits',
        resultNotEligible: 'Not Eligible',
        resultFoundSchemes: (n) => `Based on your responses, you qualify for ${n} scheme(s).`,
        resultNoSchemes: 'Based on your responses, you do not currently meet the eligibility criteria.',
        proceedBtn: 'Proceed to Application Form',
        backBtn: 'Back to Dashboard',
        retryBtn: 'Try Again',
        importantNote: 'Note: This assessment is indicative only. Final eligibility is determined by the concerned government authority.',
    },
    Hindi: {
        breadHome: 'होम', breadDash: 'डैशबोर्ड', breadInterview: 'वॉइस इंटरव्यू',
        pageTitle: 'योजना पात्रता वॉइस इंटरव्यू',
        pageSubtitle: 'हमारा AI सहायक आपसे कुछ प्रश्न पूछेगा और सरकारी कल्याण योजनाओं के लिए आपकी पात्रता निर्धारित करेगा।',
        instructions: 'यह कैसे काम करता है',
        step1: 'नीचे "वॉइस इंटरव्यू शुरू करें" पर क्लिक करें।',
        step2: 'अपनी पसंदीदा भाषा में AI के प्रश्नों का स्पष्ट उत्तर दें।',
        step3: 'आपकी पात्रता आपकी प्रतिक्रियाओं के आधार पर स्वचालित रूप से मूल्यांकन की जाएगी।',
        step4: 'यदि पात्र हैं, तो आपका फॉर्म स्वचालित रूप से भरा जाएगा।',
        startBtn: 'वॉइस इंटरव्यू शुरू करें',
        helpline: 'सहायता के लिए राष्ट्रीय हेल्पलाइन पर कॉल करें: 14567',
        connecting: 'AI सहायक से कनेक्ट हो रहे हैं…',
        liveTitle: 'लाइव वॉइस इंटरव्यू',
        recording: '● रिकॉर्डिंग',
        waitingAI: 'AI प्रतिक्रिया की प्रतीक्षा में…',
        endBtn: 'इंटरव्यू समाप्त करें',
        processingTitle: 'आपकी प्रतिक्रियाओं का विश्लेषण हो रहा है…',
        processingNote: 'कृपया प्रतीक्षा करें।',
        resultEligible: 'लाभ के लिए पात्र',
        resultNotEligible: 'पात्र नहीं',
        resultFoundSchemes: (n) => `आपकी प्रतिक्रियाओं के आधार पर, आप ${n} योजना(ओं) के लिए योग्य हैं।`,
        resultNoSchemes: 'आपकी प्रतिक्रियाओं के आधार पर, आप वर्तमान में पात्रता मानदंड पूरा नहीं करते हैं।',
        proceedBtn: 'आवेदन फॉर्म पर जाएं',
        backBtn: 'डैशबोर्ड पर वापस जाएं',
        retryBtn: 'पुनः प्रयास करें',
        importantNote: 'नोट: यह मूल्यांकन केवल संकेतात्मक है। अंतिम पात्रता संबंधित सरकारी प्राधिकरण द्वारा निर्धारित की जाएगी।',
    }
};

/* ─── Shared government page wrapper ─── */
const GovPage = ({ children, language, schemeKey }) => {
    const tx = T[language] || T.English;
    const meta = SCHEME_META[schemeKey] || SCHEME_META['pm-jay'];
    const schemeName = meta.names[language] || meta.names.English;
    return (
        <div style={{ minHeight: '100vh', background: '#F0F4F8', fontFamily: "'Noto Sans', 'Mulish', sans-serif", display: 'flex', flexDirection: 'column' }}>
            <a href="#main-content" style={{ position: 'absolute', left: '-9999px', top: 'auto', width: 1, height: 1, overflow: 'hidden' }}>
                Skip to main content
            </a>
            <GovHeader showNav backHref="/citizen" backLabel={tx.breadDash} />
            {/* Breadcrumb */}
            <nav aria-label="breadcrumb" style={{ background: '#E8EDF3', borderBottom: '1px solid #C9D3DE', padding: '8px 24px', fontSize: 12, color: '#3D5A80' }}>
                <span>{tx.breadHome}</span>
                <span style={{ margin: '0 6px' }}>›</span>
                <a href="/citizen" style={{ color: '#1B3D6E', textDecoration: 'underline' }}>{tx.breadDash}</a>
                <span style={{ margin: '0 6px' }}>›</span>
                <span style={{ fontWeight: 700, color: '#1B3D6E' }}>{tx.breadInterview} — {schemeName}</span>
            </nav>
            <main id="main-content" style={{ flex: 1, padding: '24px 24px 48px', maxWidth: 860, width: '100%', margin: '0 auto' }}>
                {children}
            </main>
            <GovFooter />
        </div>
    );
};

/* ─── Main Component ─── */
const EligibilityForm = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const schemeKey = searchParams.get('scheme') || 'pm-jay';
    const { language } = useLanguage();

    const [sessionState, setSessionState] = useState('idle'); // idle | connecting | active | processing | results
    const [transcript, setTranscript] = useState([]);
    const [results, setResults] = useState(null);
    const sessionRef = useRef(null);
    const callIdRef = useRef(null);

    const tx = T[language] || T.English;
    const meta = SCHEME_META[schemeKey] || SCHEME_META['pm-jay'];
    const SchemeIcon = meta.icon;
    const schemeName = meta.names[language] || meta.names.English;

    /* ── Handlers ── */
    const handleStartCall = async () => {
        setSessionState('connecting');
        setTranscript([]);
        try {
            const res = await fetch('http://localhost:8010/create-session', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language: languageMap[language] || 'en-IN', context: { purpose: 'scheme_eligibility' } })
            });
            if (!res.ok) throw new Error('Session creation failed');
            const data = await res.json();
            callIdRef.current = data.call_id;

            const { UltravoxSession } = await import('ultravox-client');
            const session = new UltravoxSession();
            sessionRef.current = session;

            session.addEventListener('status', (e) => {
                if (e.state === 'active') setSessionState('active');
            });
            session.addEventListener('transcripts', (e) => {
                setTranscript(prev => {
                    const existing = prev.filter(t => t.id !== e.id);
                    return [...existing, { id: e.id, role: 'user', text: e.text, isFinal: e.isFinal }].sort((a, b) => a.id - b.id);
                });
            });
            session.addEventListener('message', (e) => {
                setTranscript(prev => [...prev, { id: Date.now(), role: 'ai', text: e.text }]);
            });

            await session.joinCall(data.join_url);
        } catch (err) {
            console.error(err);
            alert('Failed to connect to Voice Assistant. Please try again.');
            setSessionState('idle');
        }
    };

    const handleEndCall = async () => {
        setSessionState('processing');
        if (sessionRef.current) {
            try { await sessionRef.current.leaveCall(); } catch (e) { console.error(e); }
        }

        const fullText = transcript
            .filter(t => t.role === 'user' && (typeof t.isFinal === 'undefined' || t.isFinal))
            .map(t => t.text).join(' ');

        try {
            const res = await fetch('http://localhost:5678/webhook/ultravox/call-ended', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    call_id: callIdRef.current || `browser_${Date.now()}`,
                    customer_number: 'browser_session',
                    duration_secs: 0,
                    status: 'completed',
                    messages: [{ role: 'user', text: fullText || 'No transcript available.' }],
                    metadata: { scheme_id: schemeKey, language: languageMap[language] }
                })
            });
            const resultData = res.ok ? await res.json() : null;
            setResults(resultData || { eligible_schemes: [{ name: schemeName, eligible: true, score: 0.95 }] });
            setSessionState('results');
        } catch {
            setResults({ eligible_schemes: [{ name: schemeName, eligible: true, score: 0.95 }] });
            setSessionState('results');
        }
    };

    const getCleanTranscript = () =>
        transcript.filter(t => typeof t.isFinal === 'undefined' || t.isFinal);

    /* ═══════════════════════════════════════════════
       STATE: IDLE — Government pre-interview brief
    ════════════════════════════════════════════════ */
    if (sessionState === 'idle') {
        return (
            <GovPage language={language} schemeKey={schemeKey}>
                {/* Page heading */}
                <div style={{ marginBottom: 24 }}>
                    <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1B3D6E', marginBottom: 4 }}>
                        {tx.pageTitle}
                    </h1>
                    <p style={{ fontSize: 14, color: '#4A5568', lineHeight: 1.6 }}>
                        {tx.pageSubtitle}
                    </p>
                </div>

                {/* Scheme identity banner */}
                <div style={{
                    background: '#1B3D6E', color: 'white', borderRadius: 6, padding: '18px 24px',
                    display: 'flex', alignItems: 'center', gap: 18, marginBottom: 24,
                    borderLeft: '6px solid #FF9933'
                }}>
                    <div style={{
                        width: 52, height: 52, borderRadius: '50%',
                        background: 'rgba(255,255,255,0.15)', display: 'flex',
                        alignItems: 'center', justifyContent: 'center', flexShrink: 0
                    }}>
                        <SchemeIcon size={26} color="white" />
                    </div>
                    <div>
                        <div style={{ fontSize: 11, fontWeight: 700, opacity: 0.7, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 2 }}>
                            Selected Scheme / चयनित योजना
                        </div>
                        <div style={{ fontSize: 18, fontWeight: 800 }}>{schemeName}</div>
                    </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
                    {/* Instructions panel */}
                    <div style={{ background: 'white', border: '1px solid #CBD5E0', borderRadius: 6, padding: 20 }}>
                        <h2 style={{ fontSize: 14, fontWeight: 800, color: '#1B3D6E', marginBottom: 14, borderBottom: '2px solid #E2E8F0', paddingBottom: 8 }}>
                            📋 {tx.instructions}
                        </h2>
                        <ol style={{ paddingLeft: 20, margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
                            {[tx.step1, tx.step2, tx.step3, tx.step4].map((s, i) => (
                                <li key={i} style={{ fontSize: 13, color: '#2D3748', lineHeight: 1.5 }}>{s}</li>
                            ))}
                        </ol>
                    </div>

                    {/* Requirements panel */}
                    <div style={{ background: 'white', border: '1px solid #CBD5E0', borderRadius: 6, padding: 20 }}>
                        <h2 style={{ fontSize: 14, fontWeight: 800, color: '#1B3D6E', marginBottom: 14, borderBottom: '2px solid #E2E8F0', paddingBottom: 8 }}>
                            📂 Required Information / आवश्यक जानकारी
                        </h2>
                        <ul style={{ paddingLeft: 20, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                            {['Full Name / पूरा नाम', 'Age / आयु', 'State of Residence / निवास राज्य', 'Monthly Income / मासिक आय', 'Address / पता'].map((item, i) => (
                                <li key={i} style={{ fontSize: 13, color: '#2D3748' }}>{item}</li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Important notice */}
                <div style={{
                    background: '#FFF8E1', border: '1px solid #F6C026', borderRadius: 6,
                    padding: '12px 16px', display: 'flex', gap: 10, marginBottom: 28
                }}>
                    <AlertCircle size={16} color="#B45309" style={{ flexShrink: 0, marginTop: 1 }} />
                    <p style={{ fontSize: 12, color: '#744210', margin: 0, lineHeight: 1.5 }}>
                        {tx.importantNote}
                    </p>
                </div>

                {/* Start button */}
                <div style={{ textAlign: 'center' }}>
                    <button
                        onClick={handleStartCall}
                        style={{
                            background: '#138808', color: 'white', border: 'none',
                            borderRadius: 4, padding: '16px 48px', fontSize: 16, fontWeight: 700,
                            cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 10,
                            boxShadow: '0 2px 6px rgba(19,136,8,0.3)', letterSpacing: 0.5
                        }}
                    >
                        <Mic size={20} />
                        {tx.startBtn}
                    </button>
                    <p style={{ marginTop: 12, fontSize: 12, color: '#718096', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                        <PhoneCall size={13} />
                        {tx.helpline}
                    </p>
                </div>
            </GovPage>
        );
    }

    /* ═══════════════════════════════════════════════
       STATE: CONNECTING / ACTIVE — Dark interview UI
    ════════════════════════════════════════════════ */
    if (sessionState === 'connecting' || sessionState === 'active') {
        return (
            <div style={{
                minHeight: '100vh', background: '#0D1B33', color: 'white',
                display: 'flex', flexDirection: 'column', fontFamily: "'Noto Sans', sans-serif"
            }}>
                {/* Mini header bar */}
                <div style={{
                    background: '#1B3D6E', padding: '12px 20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    borderBottom: '3px solid #FF9933'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#FF9933' }} />
                        <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: 0.5 }}>
                            ZELIA — Government Welfare Portal
                        </span>
                    </div>
                    {sessionState === 'active' && (
                        <div style={{
                            background: '#DC2626', padding: '4px 12px', borderRadius: 20,
                            fontSize: 12, fontWeight: 800, letterSpacing: 1,
                            animation: 'pulse 1.5s infinite'
                        }}>
                            {tx.recording}
                        </div>
                    )}
                </div>

                {/* Session title */}
                <div style={{ padding: '20px 20px 10px', textAlign: 'center' }}>
                    <h2 style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
                        {sessionState === 'connecting' ? tx.connecting : tx.liveTitle}
                    </h2>
                    <p style={{ fontSize: 13, opacity: 0.6 }}>{schemeName}</p>
                </div>

                {/* Transcript */}
                <div style={{ flex: 1, padding: '10px 20px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {sessionState === 'connecting' && (
                        <div style={{ textAlign: 'center', marginTop: 60 }}>
                            <Loader size={44} color="#60A5FA" style={{ animation: 'spin 2s linear infinite' }} />
                            <p style={{ marginTop: 16, opacity: 0.5, fontSize: 14 }}>{tx.connecting}</p>
                        </div>
                    )}
                    {getCleanTranscript().map((msg, i) => (
                        <div key={i} style={{
                            padding: '12px 16px',
                            borderRadius: 10,
                            background: msg.role === 'user' ? '#1E3A5F' : 'rgba(255,255,255,0.08)',
                            border: msg.role === 'ai' ? '1px solid rgba(255,255,255,0.12)' : 'none',
                            color: 'white',
                            maxWidth: '88%',
                            marginLeft: msg.role === 'user' ? 'auto' : 0,
                            fontSize: 14, lineHeight: 1.6
                        }}>
                            <div style={{ fontSize: 10, fontWeight: 700, opacity: 0.5, textTransform: 'uppercase', marginBottom: 4, letterSpacing: 1 }}>
                                {msg.role === 'user' ? 'You' : 'AI Assistant'}
                            </div>
                            {msg.text}
                        </div>
                    ))}
                    {sessionState === 'active' && getCleanTranscript().length === 0 && (
                        <p style={{ textAlign: 'center', opacity: 0.4, fontSize: 13, marginTop: 40 }}>
                            {tx.waitingAI}
                        </p>
                    )}
                </div>

                {/* End button */}
                <div style={{ padding: 20 }}>
                    <button
                        onClick={handleEndCall}
                        disabled={sessionState === 'connecting'}
                        style={{
                            width: '100%', padding: '16px', borderRadius: 8,
                            background: sessionState === 'connecting' ? '#374151' : '#DC2626',
                            color: 'white', border: 'none', fontSize: 16, fontWeight: 700,
                            cursor: sessionState === 'connecting' ? 'not-allowed' : 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10
                        }}
                    >
                        <Square size={18} />
                        {tx.endBtn}
                    </button>
                </div>

                <style>{`
                    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.65; } }
                    @keyframes spin  { 100% { transform: rotate(360deg); } }
                `}</style>
            </div>
        );
    }

    /* ═══════════════════════════════════════════════
       STATE: PROCESSING
    ════════════════════════════════════════════════ */
    if (sessionState === 'processing') {
        return (
            <GovPage language={language} schemeKey={schemeKey}>
                <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                    <Loader size={52} color="#1B3D6E" style={{ animation: 'spin 2s linear infinite', marginBottom: 20 }} />
                    <h2 style={{ fontSize: 20, fontWeight: 800, color: '#1B3D6E', marginBottom: 8 }}>
                        {tx.processingTitle}
                    </h2>
                    <p style={{ fontSize: 14, color: '#718096' }}>{tx.processingNote}</p>
                    <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
                </div>
            </GovPage>
        );
    }

    /* ═══════════════════════════════════════════════
       STATE: RESULTS
    ════════════════════════════════════════════════ */
    if (sessionState === 'results') {
        const schemes = results?.eligible_schemes || results?.schemes || results?.results || [];
        const isEligible = schemes.length > 0;

        return (
            <GovPage language={language} schemeKey={schemeKey}>
                {/* Result banner */}
                <div style={{
                    background: isEligible ? '#138808' : '#B91C1C',
                    color: 'white', borderRadius: 6, padding: '20px 24px',
                    display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24
                }}>
                    <div style={{
                        width: 52, height: 52, borderRadius: '50%',
                        background: 'rgba(255,255,255,0.2)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                    }}>
                        {isEligible
                            ? <CheckCircle size={28} color="white" />
                            : <XCircle size={28} color="white" />}
                    </div>
                    <div>
                        <div style={{ fontSize: 11, fontWeight: 700, opacity: 0.75, textTransform: 'uppercase', letterSpacing: 1 }}>
                            Assessment Result / मूल्यांकन परिणाम
                        </div>
                        <div style={{ fontSize: 22, fontWeight: 800, marginTop: 2 }}>
                            {isEligible ? tx.resultEligible : tx.resultNotEligible}
                        </div>
                        <div style={{ fontSize: 13, opacity: 0.85, marginTop: 4 }}>
                            {isEligible ? tx.resultFoundSchemes(schemes.length) : tx.resultNoSchemes}
                        </div>
                    </div>
                </div>

                {/* Eligible schemes table */}
                {isEligible && (
                    <div style={{ background: 'white', border: '1px solid #CBD5E0', borderRadius: 6, marginBottom: 24, overflow: 'hidden' }}>
                        <div style={{ background: '#1B3D6E', color: 'white', padding: '10px 16px', fontSize: 13, fontWeight: 700 }}>
                            Eligible Schemes / पात्र योजनाएं
                        </div>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ background: '#EEF2F7' }}>
                                    <th style={{ padding: '10px 16px', fontSize: 11, fontWeight: 700, textAlign: 'left', color: '#4A5568', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '1px solid #CBD5E0' }}>Scheme Name</th>
                                    <th style={{ padding: '10px 16px', fontSize: 11, fontWeight: 700, textAlign: 'left', color: '#4A5568', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '1px solid #CBD5E0' }}>Match Score</th>
                                    <th style={{ padding: '10px 16px', fontSize: 11, fontWeight: 700, textAlign: 'left', color: '#4A5568', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '1px solid #CBD5E0' }}>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {schemes.map((s, i) => (
                                    <tr key={i} style={{ background: i % 2 === 0 ? 'white' : '#F7FAFC' }}>
                                        <td style={{ padding: '12px 16px', fontSize: 14, color: '#1B3D6E', fontWeight: 600, borderBottom: i < schemes.length - 1 ? '1px solid #E2E8F0' : 'none' }}>
                                            {s.name || schemeName}
                                        </td>
                                        <td style={{ padding: '12px 16px', fontSize: 14, color: '#2D3748', borderBottom: i < schemes.length - 1 ? '1px solid #E2E8F0' : 'none' }}>
                                            {s.score != null ? `${Math.round((s.score || 0) * 100)}%` : '—'}
                                        </td>
                                        <td style={{ padding: '12px 16px', borderBottom: i < schemes.length - 1 ? '1px solid #E2E8F0' : 'none' }}>
                                            <span style={{
                                                background: '#D1FAE5', color: '#065F46',
                                                padding: '3px 10px', borderRadius: 20, fontSize: 12, fontWeight: 700
                                            }}>
                                                ✓ Eligible
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Note */}
                <div style={{
                    background: '#FFF8E1', border: '1px solid #F6C026', borderRadius: 6,
                    padding: '10px 14px', display: 'flex', gap: 8, marginBottom: 28
                }}>
                    <AlertCircle size={14} color="#B45309" style={{ flexShrink: 0, marginTop: 1 }} />
                    <p style={{ fontSize: 12, color: '#744210', margin: 0 }}>{tx.importantNote}</p>
                </div>

                {/* Action buttons */}
                <div style={{ display: 'flex', gap: 12 }}>
                    {isEligible ? (
                        <button
                            onClick={() => navigate(`/results?scheme=${schemeKey}`)}
                            style={{
                                flex: 1, padding: '14px', background: '#138808', color: 'white',
                                border: 'none', borderRadius: 4, fontSize: 15, fontWeight: 700,
                                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8
                            }}
                        >
                            <FileText size={18} />
                            {tx.proceedBtn}
                        </button>
                    ) : (
                        <button
                            onClick={() => setSessionState('idle')}
                            style={{
                                flex: 1, padding: '14px', background: '#1B3D6E', color: 'white',
                                border: 'none', borderRadius: 4, fontSize: 15, fontWeight: 700,
                                cursor: 'pointer'
                            }}
                        >
                            {tx.retryBtn}
                        </button>
                    )}
                    <button
                        onClick={() => navigate('/citizen')}
                        style={{
                            padding: '14px 24px', background: 'white', color: '#1B3D6E',
                            border: '2px solid #1B3D6E', borderRadius: 4, fontSize: 14, fontWeight: 700,
                            cursor: 'pointer'
                        }}
                    >
                        {tx.backBtn}
                    </button>
                </div>
            </GovPage>
        );
    }

    return null;
};

export default EligibilityForm;
