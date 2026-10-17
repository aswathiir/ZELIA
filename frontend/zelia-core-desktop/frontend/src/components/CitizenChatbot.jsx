import React, { useState, useEffect, useRef } from 'react';
import { MessageCircle, X, Send, Bot, ChevronRight, RefreshCw } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { useNavigate } from 'react-router-dom';

/* ─── Knowledge base: questions + answers in 4 languages ─── */
const KB = {
    English: [
        {
            tags: ['hello', 'hi', 'hey', 'help', 'start', 'namaste'],
            q: 'Hello! How can I help you?',
            a: 'Hello! I\'m Zelia Assistant. I can help you with schemes, eligibility, applications, and how to use this portal. What would you like to know?',
            suggestions: ['What schemes are available?', 'Check my eligibility', 'Track my application'],
        },
        {
            tags: ['scheme', 'schemes', 'available', 'list', 'all'],
            q: 'What schemes are available?',
            a: 'We currently have 6 government schemes:\n\n• **PM-JAY** – Free health insurance up to ₹5 lakh\n• **NREGA** – 100 days guaranteed rural employment\n• **Widow Pension** – Monthly pension for widows\n• **PM Awas Yojana** – Affordable housing for all\n• **Post-Matric Scholarship** – Education support for students\n• **Kisan Samman Nidhi** – ₹6,000/year for farmers\n\nWhich one would you like to know more about?',
            suggestions: ['PM-JAY details', 'NREGA details', 'Kisan Samman Nidhi details'],
        },
        {
            tags: ['pm-jay', 'pmjay', 'health', 'insurance', 'ayushman'],
            q: 'Tell me about PM-JAY',
            a: '**PM Pradhan Mantri Jan Arogya Yojana (PM-JAY)**\n\n- Free health cover of Rs.5 lakh per family per year\n- Covers secondary and tertiary hospital care\n- For BPL and low-income families\n\n**Eligibility:**\n• Family income < Rs.5 lakh/year\n• Must have BPL / Ration card\n• No existing health insurance\n\nClick "Check Eligibility" below to see if you qualify!',
            suggestions: ['Check PM-JAY eligibility', 'How to apply for PM-JAY', 'What documents are needed?'],
        },
        {
            tags: ['nrega', 'employment', 'rural', 'job', 'work', 'mgnrega'],
            q: 'Tell me about NREGA',
            a: '**National Rural Employment Guarantee Act (NREGA)**\n\n- 100 days of guaranteed employment per year\n- Minimum wage as per state government\n- Work within 5 km of your home\n\n**Eligibility:**\n• Must live in a rural area\n• Must be 18 years or older\n• Must have a Job Card\n• Family income < Rs.1 lakh/year\n\nRegister at your local Gram Panchayat for a Job Card.',
            suggestions: ['NREGA eligibility', 'How to get Job Card', 'Track NREGA application'],
        },
        {
            tags: ['pension', 'widow', 'widows', 'monthly'],
            q: 'Tell me about Widow Pension',
            a: '**Widow Pension Scheme (Indira Gandhi National Widow Pension)**\n\n- Monthly pension ranging Rs.300–Rs.500\n- For widows between 40–79 years\n- Directly transferred to bank account\n\n**Eligibility:**\n• Must be a widow\n• Age: 40 to 79 years\n• BPL / Antyodaya card holder\n• Not remarried\n\nApply at your nearest Common Service Centre (CSC).',
            suggestions: ['Widow pension eligibility', 'Apply for pension', 'How much pension will I get?'],
        },
        {
            tags: ['awas', 'housing', 'house', 'home', 'pmay'],
            q: 'Tell me about PM Awas Yojana',
            a: '**PM Awas Yojana (Housing for All)**\n\n- Subsidy on home loan interest\n- For EWS / LIG / MIG families\n- Up to Rs.2.67 lakh interest subsidy\n\n**Eligibility:**\n• Must not own a permanent house (pucca house)\n• Currently living in kutcha or temporary house\n• Household income < Rs.3 lakh/year (EWS)\n• No previous government housing benefit\n\nApply online at pmaymis.gov.in or at your CSC.',
            suggestions: ['PM Awas eligibility', 'Apply for housing scheme', 'Documents required for PM Awas'],
        },
        {
            tags: ['scholarship', 'education', 'student', 'study', 'post-matric'],
            q: 'Tell me about Post-Matric Scholarship',
            a: '**Post-Matric Scholarship Scheme**\n\n- For SC/ST/OBC/Minority students\n- Covers tuition, hostel, and other fees\n- Valid from Class 11 to PhD level\n\n**Eligibility:**\n• Studying in Class 11 or above\n• Belongs to SC, ST, OBC, or Minority community\n• Family income < Rs.2.5 lakh/year (varies by category)\n• Not receiving any other central scholarship\n\nApply at scholarships.gov.in.',
            suggestions: ['Scholarship eligibility', 'How to apply for scholarship', 'Which documents are needed?'],
        },
        {
            tags: ['kisan', 'farmer', 'farming', 'samman', 'agriculture', 'pm-kisan'],
            q: 'Tell me about PM Kisan Samman Nidhi',
            a: '**PM Kisan Samman Nidhi**\n\n- Rs.6,000 per year (Rs.2,000 every 4 months)\n- Directly credited to bank account (DBT)\n- For small and marginal farmers\n\n**Eligibility:**\n• Must own agricultural land\n• Not a government employee\n• Does not pay income tax\n• Family income < Rs.2 lakh/year\n\nRegister at pmkisan.gov.in or your nearest CSC.',
            suggestions: ['Kisan Samman eligibility', 'Check PM Kisan status', 'When will I get the amount?'],
        },
        {
            tags: ['eligib', 'eligible', 'qualify', 'check', 'fit'],
            q: 'How do I check my eligibility?',
            a: 'It\'s easy! Here\'s how:\n\n1. Go to the **Available Schemes** section on your dashboard\n2. Click on any scheme card\n3. Answer a few simple questions (takes 2–3 minutes)\n4. Get an instant eligibility result\n\nThe interview also has **voice mode** — tap the speaker icon to hear each question read aloud!',
            suggestions: ['Check PM-JAY eligibility', 'Check NREGA eligibility', 'All available schemes'],
        },
        {
            tags: ['apply', 'application', 'submit', 'register', 'enroll'],
            q: 'How do I apply for a scheme?',
            a: 'Applying is simple:\n\n**Step 1:** Click "Check Eligibility" for your chosen scheme\n**Step 2:** Complete the short interview\n**Step 3:** If eligible, click "Submit Application"\n**Step 4:** Upload required documents\n**Step 5:** Track status in "My Applications"\n\nApplications are usually processed within **14–21 working days**.',
            suggestions: ['Track my application', 'Documents required', 'What happens after I apply?'],
        },
        {
            tags: ['status', 'track', 'application', 'pending', 'approved', 'rejected', 'progress'],
            q: 'How do I track my application?',
            a: 'You can track your application status right here on the dashboard under **"My Applications"** section.\n\n- **Approved** – Your application was successful\n- **Pending** – Under review (may take 14–21 days)\n- **Rejected** – Application not approved\n\nFor rejected applications, you can re-apply after addressing the reason for rejection.',
            suggestions: ['Why was my application rejected?', 'How long does it take?', 'Reapply for scheme'],
        },
        {
            tags: ['document', 'documents', 'required', 'proof', 'needed', 'upload'],
            q: 'What documents are required?',
            a: 'Common documents needed for most schemes:\n\n• **Identity Proof** – Aadhaar Card\n• **Address Proof** – Aadhaar / Voter ID / Ration Card\n• **Income Certificate** – From Tehsildar/Revenue office\n• **Caste Certificate** – If applicable (SC/ST/OBC)\n• **Bank Passbook** – For DBT (Direct Benefit Transfer)\n• **Passport Photo** – Recent, colour\n\nSpecific schemes may need additional documents.',
            suggestions: ['Apply for a scheme', 'PM-JAY documents', 'Scholarship documents'],
        },
        {
            tags: ['time', 'how long', 'processing', 'days', 'wait'],
            q: 'How long does processing take?',
            a: 'Processing times vary by scheme:\n\n• **PM-JAY** – 7–14 working days\n• **NREGA Job Card** – 15 working days\n• **Widow Pension** – 30–45 days\n• **PM Awas Yojana** – 30–60 days\n• **Scholarship** – 30–45 days\n• **PM Kisan** – 14–21 working days\n\nEnsure all documents are correct to avoid delays.',
            suggestions: ['Track my application', 'Required documents', 'Contact support'],
        },
        {
            tags: ['login', 'log in', 'sign in', 'password', 'otp', 'aadhaar'],
            q: 'How do I log in?',
            a: 'To log in to the Citizen Portal:\n\n1. Go to the **Login** page\n2. Enter your **Aadhaar number** (12 digits)\n3. Click **Send OTP**\n4. Enter the OTP sent to your registered mobile\n5. You\'re in!\n\nYour Aadhaar is securely verified. We never store your OTP.',
            suggestions: ['Register as new user', 'Forgot Aadhaar number', 'Update mobile number'],
        },
        {
            tags: ['register', 'new user', 'sign up', 'create account', 'new'],
            q: 'How do I register?',
            a: 'New to the portal? Register in 3 simple steps:\n\n**Step 1:** Click "New? Register" on the login page\n**Step 2:** Fill in your details:\n  - Full Name\n  - Aadhaar Number\n  - Mobile Number\n  - Date of Birth\n  - Address details\n**Step 3:** Verify with OTP and set up your account\n\nRegistration takes about 5 minutes!',
            suggestions: ['Go to login', 'What documents are needed?', 'Help with registration'],
        },
        {
            tags: ['benefit', 'money', 'amount', 'receive', 'get', 'how much'],
            q: 'How much benefit will I get?',
            a: 'Benefits by scheme:\n\n• **PM-JAY** – Rs.5 lakh health cover/year\n• **NREGA** – State minimum wage x 100 days\n• **Widow Pension** – Rs.300–Rs.500/month\n• **PM Awas** – Rs.1.2–Rs.2.67 lakh subsidy\n• **Scholarship** – Varies by course and category\n• **PM Kisan** – Rs.6,000/year in 3 instalments\n\nAll benefits are directly transferred to your bank (DBT).',
            suggestions: ['Apply for a scheme', 'Check eligibility', 'Required documents'],
        },
        {
            tags: ['reject', 'rejection', 'denied', 'not approved', 'why rejected'],
            q: 'Why was my application rejected?',
            a: 'Common reasons for rejection:\n\n• **Income above limit** – Your income exceeds scheme threshold\n• **Missing documents** – Incomplete document submission\n• **Ineligible category** – Don\'t meet specific criteria\n• **Duplicate application** – Already enrolled in similar scheme\n• **Data mismatch** – Name/DOB not matching Aadhaar\n\nTip: Review the eligibility criteria and re-apply with correct documents.',
            suggestions: ['Check eligibility again', 'Required documents', 'Contact support'],
        },
        {
            tags: ['contact', 'support', 'help', 'helpline', 'call', 'complaint', 'officer'],
            q: 'How do I contact support?',
            a: 'Need help? Here\'s how to reach us:\n\n• **National Helpline** – 14555 / 1800-111-555 (Toll Free)\n• **Nearest CSC** – Visit your Common Service Centre\n• **Officer Portal** – Your assigned case officer can assist\n• **Email** – support@zeliaschemes.gov.in\n\nAvailable Monday–Saturday, 9 AM to 6 PM',
            suggestions: ['Track my application', 'Submit complaint', 'Find nearest CSC'],
        },
        {
            tags: ['thank', 'thanks', 'thank you', 'bye', 'goodbye', 'ok'],
            q: 'Thank you!',
            a: 'You\'re welcome! Feel free to ask me anything else about government schemes and benefits. I\'m here to help you access the support you deserve.',
            suggestions: ['All available schemes', 'Check my eligibility', 'Track application status'],
        },
    ],
};

/* Copy English KB to other languages (same structure — multilingual UI but English responses for now) */
KB.Hindi = KB.English;
KB.Tamil = KB.English;
KB.Malayalam = KB.English;

/* ─── Quick suggestion chips shown at start ─── */
const QUICK_CHIPS = {
    English: ['What schemes are available?', 'Check my eligibility', 'Track my application', 'Documents required'],
    Hindi: ['उपलब्ध योजनाएं', 'पात्रता जांचें', 'आवेदन ट्रैक करें', 'दस्तावेज़ चाहिए'],
    Tamil: ['திட்டங்கள் என்ன?', 'தகுதி சரிபார்க்க', 'விண்ணப்பம் கண்காணி', 'ஆவணங்கள் தேவை'],
    Malayalam: ['ലഭ്യമായ പദ്ധതികൾ', 'യോഗ്യത പരിശോധിക്കുക', 'അപേക്ഷ ട്രാക്ക് ചെയ്യുക', 'രേഖകൾ ആവശ്യം'],
};

/* ─── Simple keyword matcher ─── */
const findAnswer = (input, language) => {
    const lower = input.toLowerCase().normalize('NFC');
    const kb = KB.English; // always search English KB (responses in English for now)
    for (const entry of kb) {
        if (entry.tags.some(tag => lower.includes(tag))) return entry;
    }
    return null;
};

/* ─── Render message text with basic **bold** markdown ─── */
const RichText = ({ text }) => {
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return (
        <span style={{ whiteSpace: 'pre-line' }}>
            {parts.map((p, i) =>
                p.startsWith('**') && p.endsWith('**')
                    ? <strong key={i} style={{ color: '#0D1B33' }}>{p.slice(2, -2)}</strong>
                    : p
            )}
        </span>
    );
};

/* ══════════════════════════════════════════
   Main ChatBot Component
══════════════════════════════════════════ */
const CitizenChatbot = () => {
    const { language, t } = useLanguage();
    const navigate = useNavigate();

    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [typing, setTyping] = useState(false);
    const bottomRef = useRef(null);
    const inputRef = useRef(null);

    /* Welcome message on first open */
    useEffect(() => {
        if (open && messages.length === 0) {
            setMessages([{
                role: 'bot',
                text: 'Hi! I\'m Zelia Assistant. I can help you with:\n• Government schemes\n• Eligibility checks\n• Application tracking\n• Documents required\n\nWhat would you like to know?',
                suggestions: QUICK_CHIPS[language] || QUICK_CHIPS.English,
                id: Date.now(),
            }]);
        }
    }, [open]);

    /* Auto-scroll */
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, typing]);

    /* Focus input when opened */
    useEffect(() => {
        if (open) setTimeout(() => inputRef.current?.focus(), 300);
    }, [open]);

    const sendMessage = (text) => {
        if (!text?.trim()) return;
        const userMsg = { role: 'user', text: text.trim(), id: Date.now() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setTyping(true);

        setTimeout(() => {
            const match = findAnswer(text, language);
            const botMsg = {
                role: 'bot',
                id: Date.now() + 1,
                text: match
                    ? match.a
                    : 'I\'m not sure about that specific query. You can ask me about:\n• Government schemes (PM-JAY, NREGA, PM Kisan, etc.)\n• Eligibility criteria\n• How to apply\n• Application status\n• Required documents',
                suggestions: match?.suggestions || QUICK_CHIPS.English.slice(0, 3),
            };
            setTyping(false);
            setMessages(prev => [...prev, botMsg]);
        }, 800 + Math.random() * 400);
    };

    const handleKey = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
    };

    const reset = () => setMessages([]);

    /* ── Chat bubble ── */
    if (!open) return (
        <button
            onClick={() => setOpen(true)}
            style={{
                position: 'fixed', bottom: 24, right: 24, zIndex: 999,
                width: 58, height: 58, borderRadius: '50%',
                background: '#0D1B33', border: '2px solid #2E4D7A',
                boxShadow: '0 4px 24px rgba(6,14,31,.35)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', transition: 'transform .2s',
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.12)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
            title="Chat with Zelia Assistant"
        >
            <MessageCircle size={26} color="white" />
            {/* Unread dot */}
            <span style={{
                position: 'absolute', top: 4, right: 4, width: 12, height: 12,
                borderRadius: '50%', background: '#4ADE80', border: '2px solid #0D1B33',
                animation: 'pulse 2s ease-in-out infinite',
            }} />
        </button>
    );

    /* ── Chat panel ── */
    return (
        <div style={{
            position: 'fixed', bottom: 24, right: 24, zIndex: 999,
            width: 370, height: 560,
            background: 'white', borderRadius: 20,
            border: '1.5px solid #C0D0E0',
            boxShadow: '0 16px 56px rgba(6,14,31,.22)',
            display: 'flex', flexDirection: 'column',
            fontFamily: "'Noto Sans','Noto Sans Devanagari','Noto Sans Tamil','Noto Sans Malayalam',sans-serif",
            animation: 'slideUp .25s ease-out',
            overflow: 'hidden',
        }}>
            {/* Header */}
            <div style={{ background: '#0D1B33', padding: '14px 18px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'rgba(255,255,255,.12)', border: '1.5px solid rgba(255,255,255,.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <Bot size={20} color="white" />
                    </div>
                    <div>
                        <div style={{ color: 'white', fontWeight: 800, fontSize: 14 }}>Zelia Assistant</div>
                        <div style={{ color: '#4ADE80', fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                            <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#4ADE80', display: 'inline-block' }} />
                            Online · Typically replies instantly
                        </div>
                    </div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button onClick={reset} title="Clear chat"
                        style={{ color: 'rgba(255,255,255,.5)', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
                        <RefreshCw size={16} />
                    </button>
                    <button onClick={() => setOpen(false)}
                        style={{ color: 'rgba(255,255,255,.5)', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}>
                        <X size={18} />
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 14px 8px', display: 'flex', flexDirection: 'column', gap: 10, background: '#F5F8FC' }}>
                {messages.map(msg => (
                    <div key={msg.id} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                        <div style={{
                            maxWidth: '85%',
                            padding: '10px 14px',
                            borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '4px 18px 18px 18px',
                            background: msg.role === 'user' ? '#0D1B33' : 'white',
                            color: msg.role === 'user' ? 'white' : '#1A2A42',
                            fontSize: 13,
                            lineHeight: 1.6,
                            border: msg.role === 'bot' ? '1px solid #E2EAF4' : 'none',
                            boxShadow: '0 1px 4px rgba(6,14,31,.07)',
                        }}>
                            {msg.role === 'bot' ? <RichText text={msg.text} /> : msg.text}
                        </div>
                        {/* Suggestion chips */}
                        {msg.role === 'bot' && msg.suggestions?.length > 0 && (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8, maxWidth: '95%' }}>
                                {msg.suggestions.map((s, i) => (
                                    <button key={i} onClick={() => sendMessage(s)}
                                        style={{
                                            padding: '5px 12px', borderRadius: 20,
                                            background: 'white', border: '1.5px solid #C0D0E0',
                                            fontSize: 11, fontWeight: 700, color: '#2E4D7A',
                                            cursor: 'pointer', fontFamily: 'inherit',
                                            display: 'flex', alignItems: 'center', gap: 4,
                                            transition: 'all .15s',
                                        }}
                                        onMouseEnter={e => { e.currentTarget.style.background = '#EAF0F7'; e.currentTarget.style.borderColor = '#4F6E96'; }}
                                        onMouseLeave={e => { e.currentTarget.style.background = 'white'; e.currentTarget.style.borderColor = '#C0D0E0'; }}>
                                        <ChevronRight size={10} /> {s}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ))}

                {/* Typing indicator */}
                {typing && (
                    <div style={{ display: 'flex', alignItems: 'flex-start' }}>
                        <div style={{ padding: '10px 16px', borderRadius: '4px 18px 18px 18px', background: 'white', border: '1px solid #E2EAF4', boxShadow: '0 1px 4px rgba(6,14,31,.07)', display: 'flex', gap: 4, alignItems: 'center' }}>
                            {[0, 1, 2].map(i => (
                                <span key={i} style={{ width: 7, height: 7, borderRadius: '50%', background: '#4F6E96', display: 'inline-block', animation: `bounce 1s ease-in-out ${i * 0.2}s infinite` }} />
                            ))}
                        </div>
                    </div>
                )}
                <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div style={{ padding: '10px 12px', borderTop: '1.5px solid #E2EAF4', background: 'white', display: 'flex', gap: 8, alignItems: 'flex-end', flexShrink: 0 }}>
                <textarea
                    ref={inputRef}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKey}
                    placeholder="Ask about schemes, eligibility, documents..."
                    rows={1}
                    style={{
                        flex: 1, border: '1.5px solid #C0D0E0', borderRadius: 12,
                        padding: '9px 12px', fontSize: 13, fontFamily: 'inherit',
                        resize: 'none', outline: 'none', lineHeight: 1.5,
                        maxHeight: 80, overflowY: 'auto', color: '#0D1B33',
                        background: '#F5F8FC',
                    }}
                    onFocus={e => e.target.style.borderColor = '#4F6E96'}
                    onBlur={e => e.target.style.borderColor = '#C0D0E0'}
                />
                <button
                    onClick={() => sendMessage(input)}
                    disabled={!input.trim() || typing}
                    style={{
                        width: 38, height: 38, borderRadius: '50%', flexShrink: 0,
                        background: input.trim() && !typing ? '#0D1B33' : '#C0D0E0',
                        border: 'none', cursor: input.trim() && !typing ? 'pointer' : 'default',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'background .2s',
                    }}>
                    <Send size={16} color="white" />
                </button>
            </div>

            <style>{`
                @keyframes slideUp { from { opacity:0; transform:translateY(20px) } to { opacity:1; transform:translateY(0) } }
                @keyframes pulse { 0%,100% { transform:scale(1); opacity:1 } 50% { transform:scale(1.3); opacity:.7 } }
                @keyframes bounce { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-5px) } }
            `}</style>
        </div>
    );
};

export default CitizenChatbot;
