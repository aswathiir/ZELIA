import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, Eye, EyeOff, User, ShieldCheck } from 'lucide-react';

const Login = () => {
    const navigate = useNavigate();
    const [showPwd, setShowPwd] = useState(false);
    const [loading, setLoading] = useState(false);
    const [form, setForm] = useState({ username: '', password: '' });

    const handleLogin = (e) => {
        e.preventDefault();
        setLoading(true);
        setTimeout(() => { setLoading(false); navigate('/dashboard'); }, 1200);
    };

    return (
        <div className="login-page">



            {/* Brand */}
            <div style={{ textAlign: 'center', marginBottom: 28 }}>
                <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'rgba(255,255,255,.08)', border: '1.5px solid rgba(255,255,255,.18)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                    <ShieldCheck size={36} color="rgba(255,255,255,.8)" />
                </div>
                <h1 style={{ color: 'white', fontSize: 24, fontWeight: 900, letterSpacing: .3 }}>CHW Verification Portal</h1>
                <p style={{ color: 'rgba(255,255,255,.5)', fontSize: 14, marginTop: 6 }}>Community Health Worker Console</p>
            </div>

            {/* Card */}
            <div className="login-card">
                <div style={{ background: 'var(--ink-900)', margin: '-36px -32px 24px', padding: '14px 22px', borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0', display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Lock size={15} color="rgba(255,255,255,.7)" />
                    <span style={{ color: 'white', fontWeight: 700, fontSize: 13 }}>Secure Officer Login</span>
                </div>

                <form onSubmit={handleLogin}>
                    <div style={{ marginBottom: 16 }}>
                        <label>Officer ID / Username</label>
                        <div style={{ position: 'relative' }}>
                            <input type="text" placeholder="Enter your Officer ID"
                                value={form.username} onChange={e => setForm({ ...form, username: e.target.value })}
                                style={{ paddingLeft: 40 }} required />
                            <User size={16} style={{ position: 'absolute', left: 12, top: 14, color: 'var(--ink-400)' }} />
                        </div>
                    </div>

                    <div style={{ marginBottom: 22 }}>
                        <label>Password</label>
                        <div style={{ position: 'relative' }}>
                            <input type={showPwd ? 'text' : 'password'} placeholder="Enter your password"
                                value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
                                style={{ paddingLeft: 40, paddingRight: 40 }} required />
                            <Lock size={16} style={{ position: 'absolute', left: 12, top: 14, color: 'var(--ink-400)' }} />
                            <button type="button" onClick={() => setShowPwd(!showPwd)}
                                style={{ position: 'absolute', right: 12, top: 12, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--ink-400)' }}>
                                {showPwd ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                        </div>
                    </div>

                    <button type="submit" className="btn btn-primary btn-lg" disabled={loading}
                        style={{ width: '100%', justifyContent: 'center' }}>
                        <Lock size={16} /> {loading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>


                <div style={{ borderTop: '1px solid var(--border)', marginTop: 20, paddingTop: 16, textAlign: 'center' }}>
                    <a href="/citizen-login" style={{ fontSize: 13, color: 'var(--ink-600)', fontWeight: 600 }}>
                        Citizen / Beneficiary Login
                    </a>
                </div>
            </div>

            {/* Trust badges */}
            <div style={{ display: 'flex', gap: 10, marginTop: 24, flexWrap: 'wrap', justifyContent: 'center' }}>
                {['ISO 27001 Certified', 'Data Protected', 'Govt. of India'].map(b => (
                    <span key={b} style={{ background: 'rgba(255,255,255,.07)', color: 'rgba(255,255,255,.55)', border: '1px solid rgba(255,255,255,.12)', borderRadius: 20, fontSize: 11, padding: '4px 12px', fontWeight: 600 }}>{b}</span>
                ))}
            </div>
        </div>
    );
};

export default Login;
