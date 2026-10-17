import React from 'react';
import {
    LayoutGrid, Phone, FileText, ClipboardList,
    Settings, LogOut, Bell, FolderOpen, Activity, MessageSquare
} from 'lucide-react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import ZeliaCopilot from './ZeliaCopilot';

const NavItem = ({ to, icon: Icon, label }) => (
    <NavLink to={to} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <span className="nav-icon-wrap"><Icon size={18} /></span>
        <span>{label}</span>
    </NavLink>
);

const Layout = () => {
    const navigate = useNavigate();

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', overflow: 'hidden' }}>
            {/* Unified Premium Header */}
            <div className="app-shell-header" style={{ display: 'flex', flexDirection: 'column' }}>
                <div className="header-gov-bar">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <img src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg" alt="Satyameva Jayate" style={{ height: 20, filter: 'brightness(0) invert(1)' }} />
                        <span>Government of India</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                        <span>Digital India Service</span>
                        <select style={{ background: 'transparent', border: '1px solid rgba(255,255,255,.2)', borderRadius: 4, padding: '1px 6px', color: 'inherit', fontSize: 'inherit', fontWeight: 600, outline: 'none', cursor: 'pointer' }}>
                            <option value="en" style={{ color: '#000' }}>English</option>
                            <option value="hi" style={{ color: '#000' }}>हिन्दी</option>
                        </select>
                    </div>
                </div>

                <header className="app-header">
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                        <div style={{ width: 44, height: 44, background: 'var(--ms-green-bg)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--ms-green-light)' }}>
                            <Activity size={24} color="var(--ms-green-primary)" />
                        </div>
                        <div>
                            <div style={{ fontSize: 18, fontWeight: 900, color: 'var(--ms-navy-dark)', lineHeight: 1 }}>Administrative Console</div>
                            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--ink-400)', textTransform: 'uppercase', marginTop: 4, letterSpacing: 0.5 }}>Real-time Welfare Monitoring</div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                        <div style={{ display: 'flex', alignItems: 'center', background: 'var(--ink-50)', padding: '6px 14px', borderRadius: 10, border: '1px solid var(--border)', gap: 10 }}>
                            <div style={{ width: 8, height: 8, background: 'var(--ms-green-light)', borderRadius: '50%', boxShadow: '0 0 0 3px var(--ms-green-bg)' }} />
                            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-700)' }}>System Online</span>
                        </div>
                        <div style={{ height: 24, width: 1, background: 'var(--border)' }} />
                        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <button style={{ position: 'relative', width: 38, height: 38, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-500)', background: 'var(--ink-50)', border: '1px solid var(--border)', cursor: 'pointer' }}>
                                <Bell size={18} />
                                <span style={{ position: 'absolute', top: -2, right: -2, width: 10, height: 10, background: 'var(--ms-gold)', borderRadius: '50%', border: '2px solid white' }} />
                            </button>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 4, paddingRight: 12, background: 'var(--ink-50)', borderRadius: 12, border: '1px solid var(--border)', cursor: 'pointer' }}>
                                <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--ms-navy-dark)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', fontWeight: 800, fontSize: 11 }}>
                                    CHW
                                </div>
                                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ms-navy-dark)' }}>Admin</div>
                            </div>
                        </div>
                    </div>
                </header>
            </div>

            <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
                {/* 1. SIDEBAR */}
                <aside className="app-sidebar" style={{ width: 260, background: 'var(--ink-50)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ padding: '32px 24px 20px 24px' }}>
                        <div style={{ fontSize: 24, fontWeight: 900, color: 'var(--ms-navy-dark)', letterSpacing: -0.5 }}>ZELIA</div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--ink-400)', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 2 }}>Welfare Portal</div>
                    </div>

                    <nav className="sidebar-nav" style={{ padding: '0 14px', flex: 1 }}>
                        <p className="nav-section-label">Registry</p>
                        <NavItem to="/dashboard" icon={LayoutGrid} label="Dashboard" />
                        <NavItem to="/active-calls" icon={Phone} label="Live Telemetry" />
                        <NavItem to="/schemes" icon={FileText} label="Official Schemes" />
                        <NavItem to="/documents" icon={FolderOpen} label="Document Vault" />

                        <p className="nav-section-label" style={{ marginTop: 20 }}>System</p>
                        <NavItem to="/history" icon={ClipboardList} label="Audit Logs" />
                        <NavItem to="/settings" icon={Settings} label="Settings" />
                    </nav>

                    <div className="sidebar-footer" style={{ padding: 20, borderTop: '1px solid var(--border)' }}>
                        <button onClick={() => navigate('/login')}
                            style={{ display: 'flex', alignItems: 'center', gap: 10, color: 'var(--ink-600)', fontSize: 13, fontWeight: 700, width: '100%', padding: '12px', background: 'white', border: '1px solid var(--border)', borderRadius: 10, cursor: 'pointer', transition: 'all 0.2s' }}>
                            <LogOut size={16} /> Sign Out
                        </button>
                    </div>
                </aside>

                {/* 2. MAIN CONTENT AREA */}
                <main style={{ flex: 1, display: 'flex', flexDirection: 'column', background: 'var(--ink-0)', overflow: 'hidden' }}>
                    <div style={{ flex: 1, overflowY: 'auto' }}>
                        <div className="page-wrap animate-in" style={{ padding: 32, maxWidth: 1200, margin: '0 auto' }}>
                            <Outlet />
                        </div>
                    </div>
                </main>

                {/* 3. RIGHT PANEL */}
                <aside style={{ width: 340, background: 'var(--surface-alt)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
                    <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border)', background: 'white' }}>
                        <div style={{ fontWeight: 800, fontSize: 15, color: 'var(--ms-green-primary)', display: 'flex', alignItems: 'center', gap: 8 }}>
                            <MessageSquare size={18} /> ZELIA Copilot
                        </div>
                        <div style={{ fontSize: 12, color: 'var(--ink-500)', marginTop: 2 }}>Secure RAG Agent & Automation</div>
                    </div>

                    <div style={{ flex: 1, padding: 24, overflowY: 'hidden', display: 'flex', flexDirection: 'column', gap: 24 }}>
                        <ZeliaCopilot />
                    </div>
                </aside>
            </div>
        </div>
    );
};

export default Layout;
