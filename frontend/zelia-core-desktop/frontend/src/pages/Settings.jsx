import React, { useState } from 'react';
import { User, Globe, Bell, Shield, ChevronRight, Save } from 'lucide-react';

const Settings = () => {
    const [saved, setSaved] = useState(false);
    const [language, setLanguage] = useState('English');
    const [profile, setProfile] = useState({ name: 'Officer J. Desai', id: 'OFF-2024-042', district: 'Pune, Maharashtra', phone: '+91 98765 43210' });
    const [notif, setNotif] = useState({ newApp: true, callReminder: true, weeklyReport: false });

    const save = () => { setSaved(true); setTimeout(() => setSaved(false), 2500); };
    const setField = (k) => (e) => setProfile(p => ({ ...p, [k]: e.target.value }));
    const toggle = (k) => () => setNotif(n => ({ ...n, [k]: !n[k] }));

    const Section = ({ icon: Icon, title, children }) => (
        <div className="card" style={{ marginBottom: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18, paddingBottom: 14, borderBottom: '1.5px solid var(--border)' }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: 'var(--ink-100)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon size={18} color="var(--ink-600)" />
                </div>
                <h2 style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink-900)' }}>{title}</h2>
            </div>
            {children}
        </div>
    );

    const Toggle = ({ checked, onChange, label }) => (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink-700)' }}>{label}</span>
            <button type="button" onClick={onChange}
                style={{ width: 44, height: 24, borderRadius: 12, position: 'relative', border: 'none', cursor: 'pointer', padding: 0, transition: 'background .2s', background: checked ? 'var(--ink-900)' : 'var(--ink-200)' }}>
                <span style={{ position: 'absolute', top: 3, left: checked ? 22 : 3, width: 18, height: 18, borderRadius: '50%', background: 'white', transition: 'left .2s', boxShadow: '0 1px 4px rgba(0,0,0,.2)' }} />
            </button>
        </div>
    );

    return (
        <div style={{ maxWidth: 660 }}>
            <div style={{ marginBottom: 24 }}>
                <h1 className="page-title">Settings</h1>
                <p className="page-subtitle">Account and preferences</p>
            </div>

            <Section icon={User} title="Officer Profile">
                <div style={{ display: 'grid', gap: 14 }}>
                    <div className="grid-2">
                        <div><label>Full Name</label><input value={profile.name} onChange={setField('name')} /></div>
                        <div><label>Officer ID</label><input value={profile.id} readOnly style={{ background: 'var(--ink-50)', color: 'var(--text-muted)', cursor: 'not-allowed' }} /></div>
                    </div>
                    <div className="grid-2">
                        <div><label>District</label><input value={profile.district} onChange={setField('district')} /></div>
                        <div><label>Mobile</label><input value={profile.phone} onChange={setField('phone')} /></div>
                    </div>
                </div>
            </Section>

            <Section icon={Globe} title="Language Preference">
                <div style={{ display: 'flex', gap: 10 }}>
                    {['English', 'Hindi'].map(l => (
                        <button key={l} onClick={() => setLanguage(l)}
                            style={{
                                padding: '11px 26px', borderRadius: 8, fontWeight: 700, fontSize: 14, fontFamily: 'inherit', cursor: 'pointer', border: '1.5px solid', transition: 'all .15s',
                                background: language === l ? 'var(--ink-900)' : 'white',
                                color: language === l ? 'white' : 'var(--ink-600)',
                                borderColor: language === l ? 'var(--ink-900)' : 'var(--border)',
                            }}>
                            {l}
                        </button>
                    ))}
                </div>
            </Section>

            <Section icon={Bell} title="Notifications">
                <Toggle checked={notif.newApp} onChange={toggle('newApp')} label="New applications" />
                <Toggle checked={notif.callReminder} onChange={toggle('callReminder')} label="Call reminders" />
                <Toggle checked={notif.weeklyReport} onChange={toggle('weeklyReport')} label="Weekly report emails" />
            </Section>

            <Section icon={Shield} title="Security">
                <button style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '13px 0', background: 'none', border: 'none', borderBottom: '1px solid var(--border)', cursor: 'pointer', fontFamily: 'inherit', fontSize: 14, fontWeight: 600, color: 'var(--ink-700)' }}>
                    <span>Change Password</span>
                    <ChevronRight size={16} color="var(--ink-400)" />
                </button>
                <button style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', padding: '13px 0', background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'inherit', fontSize: 14, fontWeight: 600, color: 'var(--ink-700)' }}>
                    <span>Two-Factor Authentication</span>
                    <ChevronRight size={16} color="var(--ink-400)" />
                </button>
            </Section>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button className="btn btn-primary btn-lg" onClick={save}>
                    <Save size={16} /> {saved ? 'Saved' : 'Save Changes'}
                </button>
            </div>
        </div>
    );
};

export default Settings;
