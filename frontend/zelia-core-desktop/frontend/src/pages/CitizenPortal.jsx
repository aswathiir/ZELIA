import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    CheckCircle, Clock, Heart, Wheat, Home, Folder,
    PlusCircle, AlertCircle, FileText, Phone, Mic
} from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import GovHeader, { GovFooter } from '../components/GovHeader';
import { getAuthHeaders } from '../utils/api';

/* ── Scheme meta ── */
const SCHEME_NAMES = {
    English: {
        'pm-jay': 'PM-JAY Health Insurance',
        'nrega': 'NREGA Rural Employment',
        'awas': 'PM Awas Yojana',
        'kisan': 'PM Kisan Samman Nidhi',
        'pension': 'National Social Assistance',
        'scholarship': 'Post-Matric Scholarship',
    },
    Hindi: {
        'pm-jay': 'PM-JAY स्वास्थ्य बीमा',
        'nrega': 'नरेगा ग्रामीण रोजगार',
        'awas': 'PM आवास योजना',
        'kisan': 'PM किसान सम्मान निधि',
        'pension': 'राष्ट्रीय सामाजिक सहायता',
        'scholarship': 'पोस्ट-मैट्रिक छात्रवृत्ति',
    },
    Tamil: {
        'pm-jay': 'PM-JAY சுகாதார காப்பீடு',
        'nrega': 'நரேகா கிராம வேலை',
        'awas': 'PM Awas Yojana',
        'kisan': 'PM கிசான் சம்மான் நிதி',
        'pension': 'தேசிய சமூக உதவி',
        'scholarship': 'மேல்நிலை கல்வி உதவித்தொகை',
    },
    Malayalam: {
        'pm-jay': 'PM-JAY ആരോഗ്യ ഇൻഷ്വറൻസ്',
        'nrega': 'നരേഗ ഗ്രാമീണ തൊഴിൽ',
        'awas': 'PM ആവാസ് യോജന',
        'kisan': 'കിസാൻ സമ്മാൻ നിധി',
        'pension': 'ദേശീയ സാമൂഹ്യ സഹായം',
        'scholarship': ' സ്കോളർഷിപ്പ്',
    }
};

const SCHEME_ICONS = { 'pm-jay': Heart, 'nrega': Wheat, 'awas': Home };

/* ── Status row in application table ── */
const StatusRow = ({ app, names, userId, language }) => {
    const Icon = SCHEME_ICONS[app.schemeKey] || FileText;
    const schemeName = (names[app.schemeKey]) || app.schemeKey;

    let statusBg = '#E3F2FD', statusColor = '#0D47A1', statusLabel = 'Pending';
    let statusHi = 'लंबित';
    if (app.status === 'Approved') {
        statusBg = '#E8F5E9'; statusColor = '#1B5E20';
        statusLabel = 'Approved'; statusHi = 'स्वीकृत';
    } else if (app.status === 'Needs_Documents') {
        statusBg = '#FFF8E1'; statusColor = '#E65100';
        statusLabel = 'Action Required'; statusHi = 'कार्रवाई आवश्यक';
    }

    const displayLabel = language === 'Hindi' ? statusHi : statusLabel;

    return (
        <tr>
            <td style={{ padding: '14px 16px', borderBottom: '1px solid #E8EEF5', verticalAlign: 'top' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 40, height: 40, borderRadius: 8, background: '#EEF2F7', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                        <Icon size={20} color="#1B3D6E" />
                    </div>
                    <div>
                        <div style={{ fontSize: 14, fontWeight: 800, color: '#1B3D6E' }}>{schemeName}</div>
                        {app.documentName && <div style={{ fontSize: 12, color: '#777', marginTop: 2 }}>{app.documentName}</div>}
                    </div>
                </div>
            </td>
            <td style={{ padding: '14px 16px', borderBottom: '1px solid #E8EEF5', verticalAlign: 'top' }}>
                <span style={{ display: 'inline-block', background: statusBg, color: statusColor, border: `1px solid ${statusColor}30`, borderRadius: 3, padding: '4px 10px', fontSize: 12, fontWeight: 800, letterSpacing: 0.3 }}>
                    {displayLabel}
                </span>
                {/* Missing fields list */}
                {app.status === 'Needs_Documents' && app.missingFields?.length > 0 && (
                    <div style={{ marginTop: 8, padding: '8px 10px', background: '#FFF3E0', border: '1px solid #FFB74D', borderRadius: 3, fontSize: 12 }}>
                        <div style={{ fontWeight: 800, color: '#BF360C', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 5 }}>
                            <AlertCircle size={12} /> Missing documents:
                        </div>
                        <ul style={{ margin: 0, paddingLeft: 16 }}>
                            {app.missingFields.map(f => <li key={f} style={{ color: '#6D4C41', fontWeight: 600 }}>{f}</li>)}
                        </ul>
                        <a href={`/citizen/documents?hash=${userId}`} style={{ display: 'block', marginTop: 6, color: '#1B3D6E', fontWeight: 700, textDecoration: 'underline', fontSize: 11 }}>
                            → Upload in Document Vault
                        </a>
                    </div>
                )}
                {/* PDF download when ready */}
                {app.status === 'Approved' && app.filledPdfUri && (
                    <a href={`http://localhost:8009/households/${userId}/files/${app.filledPdfUri.replace('minio://', '')}`}
                        target="_blank" rel="noreferrer"
                        style={{ display: 'inline-flex', alignItems: 'center', gap: 5, marginTop: 8, color: '#1B3D6E', fontSize: 12, fontWeight: 700, textDecoration: 'none', background: '#E3F2FD', padding: '5px 10px', borderRadius: 3, border: '1px solid #90CAF9' }}>
                        <FileText size={12} /> Download Filled Form / भरा हुआ फॉर्म
                    </a>
                )}
            </td>
        </tr>
    );
};

/* ── Action tile (large accessible button) ── */
const ActionTile = ({ icon: Icon, titleEn, titleHi, descEn, descHi, color, onClick, language }) => (
    <button onClick={onClick} style={{
        flex: 1, minWidth: 150, padding: '18px 16px',
        background: 'white', border: `2px solid ${color}40`,
        borderTop: `4px solid ${color}`,
        borderRadius: 4, cursor: 'pointer', textAlign: 'left',
        boxShadow: '0 2px 6px rgba(0,0,0,.06)', transition: 'all .18s',
        display: 'flex', flexDirection: 'column', gap: 10
    }}
        onMouseOver={e => { e.currentTarget.style.background = `${color}08`; e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,.10)'; }}
        onMouseOut={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.boxShadow = '0 2px 6px rgba(0,0,0,.06)'; }}>
        <div style={{ width: 44, height: 44, borderRadius: 8, background: `${color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon size={22} color={color} />
        </div>
        <div>
            <div style={{ fontSize: 14, fontWeight: 900, color: '#1B3D6E', lineHeight: 1.2 }}>
                {language === 'Hindi' ? titleHi : titleEn}
            </div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 3, lineHeight: 1.4 }}>
                {language === 'Hindi' ? descHi : descEn}
            </div>
        </div>
    </button>
);

/* ── Main CitizenPortal ── */
const CitizenPortal = () => {
    const navigate = useNavigate();
    const { language } = useLanguage();
    const names = SCHEME_NAMES[language] || SCHEME_NAMES.English;

    const [apps, setApps] = useState([]);
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);

    const userId = new URLSearchParams(window.location.search).get('hash')
        || localStorage.getItem('zelia_user_id');

    useEffect(() => {
        if (!userId) { setLoading(false); return; }

        const loadPortalData = async () => {
            let gotRecommendation = false;

            /* 1. Load submissions */
            try {
                const res = await fetch(`http://localhost:8009/submissions/session/${userId}`, {
                    headers: getAuthHeaders()
                });
                if (res.ok) {
                    const data = await res.json();
                    const mappedApps = data.submissions.map(sub => {
                        let status = 'Pending';
                        let missing = [];
                        if (['verified', 'approved', 'pdf_ready', 'auto_processed'].includes(sub.status)) {
                            status = 'Approved';
                        }
                        if (['incomplete_fields', 'rejected', 'needs_documents'].includes(sub.status)) {
                            status = 'Needs_Documents';
                            missing = sub.correction_required_fields || [];
                        }
                        return {
                            id: sub.submission_id,
                            schemeKey: sub.scheme_id || sub.metadata?.scheme_id || 'pm-jay',
                            status,
                            missingFields: missing,
                            filledPdfUri: sub.filled_pdf_uri || null,
                            documentName: sub.metadata?.original_filename || null,
                        };
                    });
                    setApps(mappedApps);
                }
            } catch (e) { console.error('Failed to load submissions:', e); }

            /* 2. Load recommendations from last call */
            try {
                const res = await fetch(`http://localhost:8013/households/${userId}`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.success && data.suggestions?.length) {
                        setRecommendations(data.suggestions);
                        gotRecommendation = true;
                    }
                }
            } catch { /* noop */ }

            /* 3. Fallback from workflow-status */
            if (!gotRecommendation) {
                try {
                    const res = await fetch(`http://localhost:8013/households/${userId}/workflow-status`);
                    if (res.ok) {
                        const data = await res.json();
                        const best = data?.best_match_scheme || {};
                        if (best.scheme_id || best.scheme_name) {
                            setRecommendations([{
                                scheme_id: best.scheme_id || 'best-match',
                                scheme_name: best.scheme_name || best.scheme_id,
                                benefits: best.benefits || 'Suggested based on your latest call and uploaded documents.',
                            }]);
                        }
                    }
                } catch { /* noop */ }
            }

            setLoading(false);
        };
        loadPortalData();
    }, [userId]);

    const greetHour = new Date().getHours();
    const greeting = greetHour < 12 ? 'Good Morning' : greetHour < 17 ? 'Good Afternoon' : 'Good Evening';
    const greetingHi = greetHour < 12 ? 'सुप्रभात' : greetHour < 17 ? 'शुभ दोपहर' : 'शुभ संध्या';

    return (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: '#EEF2F7', fontFamily: "'Noto Sans','Noto Sans Devanagari',sans-serif" }}>
            <GovHeader backHref={null} />

            <main id="main-content" style={{ flex: 1, maxWidth: 780, width: '100%', margin: '0 auto', padding: '24px 16px 48px' }}>

                {/* Breadcrumb */}
                <div style={{ fontSize: 12, color: '#555', marginBottom: 16 }}>
                    <a href="/" style={{ color: '#1B3D6E', textDecoration: 'none', fontWeight: 600 }}>Home</a>
                    <span style={{ margin: '0 6px', color: '#999' }}>›</span>
                    <span style={{ fontWeight: 700, color: '#333' }}>Citizen Dashboard</span>
                </div>

                {/* Welcome banner */}
                <div style={{ background: '#1B3D6E', borderRadius: 4, padding: '16px 20px', marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
                    <div>
                        <div style={{ color: 'rgba(255,255,255,.7)', fontSize: 12, fontWeight: 600 }}>
                            {language === 'Hindi' ? greetingHi : greeting}
                        </div>
                        <div style={{ color: 'white', fontSize: 18, fontWeight: 900, marginTop: 2 }}>
                            {language === 'Hindi' ? 'आपके आवेदन का डैशबोर्ड' : 'Your Application Dashboard'}
                        </div>
                        <div style={{ color: 'rgba(255,255,255,.6)', fontSize: 12, marginTop: 4 }}>
                            Zelia — Welfare Scheme Access Portal &nbsp;|&nbsp; कल्याण योजना पहुँच पोर्टल
                        </div>
                    </div>
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                        <span style={{ background: 'rgba(255,255,255,.12)', color: 'rgba(255,255,255,.85)', fontSize: 11, padding: '4px 10px', borderRadius: 20, fontWeight: 700 }}>
                            {apps.length} Application{apps.length !== 1 ? 's' : ''}
                        </span>
                        <span style={{ background: 'rgba(19,136,8,.3)', color: '#90EE90', fontSize: 11, padding: '4px 10px', borderRadius: 20, fontWeight: 700 }}>
                            ● Portal Online
                        </span>
                    </div>
                </div>

                {/* Quick actions */}
                <div style={{ marginBottom: 24 }}>
                    <h2 style={{ fontSize: 15, fontWeight: 900, color: '#1B3D6E', margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                        {language === 'Hindi' ? 'त्वरित क्रियाएँ' : 'Quick Actions'}
                    </h2>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                        <ActionTile
                            icon={Mic} color="#1B3D6E"
                            titleEn="Start Voice Interview"   titleHi="वॉइस इंटरव्यू शुरू करें"
                            descEn="Check scheme eligibility via AI call"  descHi="AI कॉल द्वारा पात्रता जाँचें"
                            onClick={() => navigate('/eligibility')} language={language} />
                        <ActionTile
                            icon={Folder} color="#FF9933"
                            titleEn="Open Document Vault"  titleHi="दस्तावेज़ वॉल्ट खोलें"
                            descEn="Upload & manage your documents"  descHi="दस्तावेज़ अपलोड और प्रबंधित करें"
                            onClick={() => navigate('/citizen/documents')} language={language} />
                        <ActionTile
                            icon={PlusCircle} color="#138808"
                            titleEn="New Application"  titleHi="नया आवेदन"
                            descEn="Apply for a government scheme"  descHi="सरकारी योजना के लिए आवेदन करें"
                            onClick={() => navigate('/eligibility')} language={language} />
                        <ActionTile
                            icon={Phone} color="#7B1FA2"
                            titleEn="Helpline"  titleHi="हेल्पलाइन"
                            descEn="1800-XXX-XXXX (Toll Free)"  descHi="1800-XXX-XXXX (निःशुल्क)"
                            onClick={() => window.open('tel:1800XXXXXXX')} language={language} />
                    </div>
                </div>

                {/* Scheme recommendations */}
                {recommendations.length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                            <h2 style={{ fontSize: 15, fontWeight: 900, color: '#1B3D6E', margin: 0, textTransform: 'uppercase', letterSpacing: 0.5 }}>
                                {language === 'Hindi' ? 'अनुशंसित योजनाएँ' : 'Recommended Schemes'}
                            </h2>
                            <span style={{ background: '#E3F2FD', color: '#0D47A1', fontSize: 11, padding: '3px 8px', borderRadius: 20, fontWeight: 700, border: '1px solid #90CAF9' }}>
                                <Clock size={10} style={{ verticalAlign: 'middle', marginRight: 3 }} />
                                Based on last call
                            </span>
                        </div>

                        <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4 }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ background: '#F0F4FA' }}>
                                        <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 800, color: '#444', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '2px solid #D8E0EA' }}>Scheme / योजना</th>
                                        <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 800, color: '#444', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '2px solid #D8E0EA' }}>Benefits / लाभ</th>
                                        <th style={{ padding: '10px 16px', textAlign: 'right', fontSize: 11, fontWeight: 800, color: '#444', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '2px solid #D8E0EA' }}>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recommendations.map((rec, idx) => (
                                        <tr key={idx} style={{ background: idx % 2 === 0 ? 'white' : '#FAFBFD' }}>
                                            <td style={{ padding: '12px 16px', borderBottom: '1px solid #E8EEF5', fontSize: 14, fontWeight: 800, color: '#1B3D6E' }}>
                                                {rec.scheme_name || rec.title || rec.scheme_id}
                                            </td>
                                            <td style={{ padding: '12px 16px', borderBottom: '1px solid #E8EEF5', fontSize: 13, color: '#555', lineHeight: 1.5 }}>
                                                {rec.benefits || 'Eligible based on your profile'}
                                            </td>
                                            <td style={{ padding: '12px 16px', borderBottom: '1px solid #E8EEF5', textAlign: 'right' }}>
                                                <button onClick={() => navigate(`/eligibility?scheme=${rec.scheme_id}`)}
                                                    style={{ padding: '7px 16px', borderRadius: 3, border: '1.5px solid #1B3D6E', background: '#1B3D6E', color: 'white', fontSize: 12, fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit', transition: 'background .15s' }}
                                                    onMouseOver={e => e.currentTarget.style.background = '#142d52'}
                                                    onMouseOut={e => e.currentTarget.style.background = '#1B3D6E'}>
                                                    Apply Now →
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* My Applications table */}
                <div>
                    <h2 style={{ fontSize: 15, fontWeight: 900, color: '#1B3D6E', margin: '0 0 12px', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                        {language === 'Hindi' ? 'मेरे आवेदन' : 'My Applications'}
                    </h2>

                    <div style={{ background: 'white', border: '1px solid #CCD3DC', borderRadius: 4, overflow: 'hidden' }}>

                        {/* Status legend */}
                        <div style={{ padding: '10px 16px', background: '#F0F4FA', borderBottom: '1px solid #D8E0EA', display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                            {[
                                { color: '#1B5E20', bg: '#E8F5E9', label: 'Approved' },
                                { color: '#0D47A1', bg: '#E3F2FD', label: 'Pending Review' },
                                { color: '#E65100', bg: '#FFF8E1', label: 'Action Required' },
                            ].map(s => (
                                <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}>
                                    <div style={{ width: 10, height: 10, borderRadius: 2, background: s.bg, border: `1px solid ${s.color}50` }} />
                                    <span style={{ fontWeight: 600, color: '#444' }}>{s.label}</span>
                                </div>
                            ))}
                        </div>

                        {loading ? (
                            <div style={{ padding: '40px', textAlign: 'center', color: '#777' }}>
                                <Clock size={32} color="#CCC" style={{ marginBottom: 8 }} />
                                <div style={{ fontSize: 14, fontWeight: 600 }}>Loading applications…</div>
                            </div>
                        ) : apps.length === 0 ? (
                            <div style={{ padding: '40px', textAlign: 'center' }}>
                                <Folder size={40} color="#CCC" style={{ marginBottom: 10 }} />
                                <div style={{ fontSize: 15, fontWeight: 800, color: '#555', marginBottom: 4 }}>
                                    {language === 'Hindi' ? 'अभी तक कोई आवेदन नहीं' : 'No Applications Yet'}
                                </div>
                                <div style={{ fontSize: 13, color: '#888', marginBottom: 18 }}>
                                    {language === 'Hindi'
                                        ? 'वॉइस इंटरव्यू शुरू करें या दस्तावेज़ अपलोड करें।'
                                        : 'Start a voice interview or upload documents to begin.'}
                                </div>
                                <button onClick={() => navigate('/eligibility')}
                                    style={{ padding: '10px 20px', borderRadius: 3, border: 'none', background: '#1B3D6E', color: 'white', fontSize: 13, fontWeight: 800, cursor: 'pointer', fontFamily: 'inherit' }}>
                                    {language === 'Hindi' ? '+ नया आवेदन शुरू करें' : '+ Start New Application'}
                                </button>
                            </div>
                        ) : (
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ background: '#F0F4FA' }}>
                                        <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 800, color: '#444', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '2px solid #D8E0EA', width: '55%' }}>
                                            Scheme / योजना
                                        </th>
                                        <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 11, fontWeight: 800, color: '#444', textTransform: 'uppercase', letterSpacing: 0.7, borderBottom: '2px solid #D8E0EA' }}>
                                            Status / स्थिति
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {apps.map((app, idx) => (
                                        <tr key={app.id} style={{ background: idx % 2 === 0 ? 'white' : '#FAFBFD' }}>
                                            <StatusRow app={app} names={names} userId={userId} language={language} />
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>

                {/* Notice section */}
                <div style={{ marginTop: 24, background: '#FFF8E1', border: '1px solid #FFE082', borderLeft: '4px solid #FF9800', borderRadius: 4, padding: '14px 18px', fontSize: 13, color: '#5D4037' }}>
                    <div style={{ fontWeight: 800, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <AlertCircle size={14} /> Important Notice / महत्वपूर्ण सूचना
                    </div>
                    <p style={{ margin: 0, lineHeight: 1.6 }}>
                        All government scheme applications are processed in 15–30 working days.
                        Keep your documents updated in your Document Vault for faster processing.
                        &nbsp;|&nbsp; सभी सरकारी योजना आवेदन 15-30 कार्य दिवसों में संसाधित होते हैं।
                    </p>
                </div>
            </main>

            <GovFooter />
        </div>
    );
};

export default CitizenPortal;
