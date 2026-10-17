import React, { useState, useEffect } from 'react';
import { Search, AlertCircle, ExternalLink } from 'lucide-react';

/* Category → Ashoka-emblem style icon URLs (placeholder small govt icons) */
const GOV_ICONS = {
    health: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/40px-Emblem_of_India.svg.png',
    employment: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/40px-Emblem_of_India.svg.png',
    pension: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/40px-Emblem_of_India.svg.png',
    housing: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/40px-Emblem_of_India.svg.png',
    agriculture: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/40px-Emblem_of_India.svg.png',
    education: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/40px-Emblem_of_India.svg.png',
    general: 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/55/Emblem_of_India.svg/40px-Emblem_of_India.svg.png',
};

const FILTER_TABS = ['All', 'Central Schemes', 'State Schemes'];

const Schemes = () => {
    const [query, setQuery] = useState('');
    const [schemes, setSchemes] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState('All');
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 12;

    useEffect(() => {
        const fetchSchemes = async () => {
            try {
                const res = await fetch('http://127.0.0.1:8016/schemes');
                if (res.ok) {
                    const data = await res.json();
                    const mapped = data.map(s => ({
                        id: s.scheme_id,
                        name: s.name || 'Unnamed Scheme',
                        description: s.description || s.benefits || `Government welfare scheme under ${s.ministry || 'Ministry of Social Welfare'}`,
                        eligibility: s.eligibility || s.eligibility_criteria || 'Eligible citizens as per government guidelines',
                        ministry: s.ministry || 'General',
                        category: (s.ministry || '').toLowerCase().includes('state') ? 'State Schemes' : 'Central Schemes',
                        status: s.status || 'active',
                        icon: GOV_ICONS[(s.ministry || 'general').toLowerCase().split(' ')[0]] || GOV_ICONS.general,
                    }));
                    setSchemes(mapped);
                } else {
                    console.error('Failed to load schemes. HTTP Status:', res.status);
                }
            } catch (err) {
                console.error('Network error fetching schemes:', err);
            } finally {
                setLoading(false);
            }
        };
        fetchSchemes();
    }, []);

    const filtered = schemes
        .filter(s => activeFilter === 'All' || s.category === activeFilter)
        .filter(s =>
            (s.name || '').toLowerCase().includes(query.toLowerCase()) ||
            (s.description || '').toLowerCase().includes(query.toLowerCase()) ||
            (s.ministry || '').toLowerCase().includes(query.toLowerCase())
        );

    const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
    const paginated = filtered.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE);

    const handleSchemeClick = (schemeName) => {
        const searchQuery = encodeURIComponent(schemeName + ' government scheme india official');
        window.open(`https://www.google.com/search?q=${searchQuery}`, '_blank');
    };

    /* Reset page on filter/search change */
    useEffect(() => { setCurrentPage(1); }, [query, activeFilter]);

    return (
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 8, paddingTop: 8 }}>
                <img src={GOV_ICONS.general} alt="Emblem" style={{ width: 36, height: 36, opacity: 0.8 }} onError={e => e.target.style.display = 'none'} />
                <div>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--ink-500)' }}>Official Government Schemes</div>
                    <div style={{ fontSize: 11, color: 'var(--ink-400)' }}>GOVERNMENT OF INDIA</div>
                </div>
            </div>

            {/* Title & Count */}
            <div style={{ textAlign: 'center', marginBottom: 24, marginTop: 16 }}>
                <h1 style={{ fontSize: 28, fontWeight: 900, color: '#1a202c', margin: 0 }}>Official Government Schemes</h1>
                <p style={{ fontSize: 14, color: 'var(--ink-500)', marginTop: 6 }}>{schemes.length} schemes available</p>
            </div>

            {/* Search Bar */}
            <div style={{ position: 'relative', maxWidth: 520, margin: '0 auto 20px' }}>
                <Search size={18} style={{ position: 'absolute', left: 14, top: 13, color: 'var(--ink-400)' }} />
                <input
                    type="text"
                    placeholder="Search for schemes, keywords, or benefits..."
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    style={{
                        paddingLeft: 42, height: 46, width: '100%', borderRadius: 10,
                        border: '1.5px solid #e2e8f0', background: 'white', fontSize: 14,
                        fontWeight: 500, outline: 'none', boxShadow: '0 1px 3px rgba(0,0,0,0.06)'
                    }}
                />
            </div>

            {/* Filter Tabs */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 8, marginBottom: 28 }}>
                {FILTER_TABS.map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveFilter(tab)}
                        style={{
                            padding: '8px 20px', borderRadius: 20, fontSize: 13, fontWeight: 700,
                            border: activeFilter === tab ? '2px solid #2563eb' : '1.5px solid #e2e8f0',
                            background: activeFilter === tab ? '#2563eb' : 'white',
                            color: activeFilter === tab ? 'white' : '#64748b',
                            cursor: 'pointer', transition: 'all 0.2s'
                        }}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            {/* Loading / Empty */}
            {loading ? (
                <div style={{ textAlign: 'center', padding: 60, color: 'var(--ink-500)', fontSize: 14 }}>
                    Synchronizing Government Records...
                </div>
            ) : filtered.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 60, color: 'var(--ink-500)', fontSize: 14 }}>
                    <AlertCircle size={32} color="var(--ink-300)" style={{ marginBottom: 10 }} />
                    <div>No schemes match your search.</div>
                </div>
            ) : (
                <>
                    {/* Scheme Cards Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: 20, marginBottom: 32 }}>
                        {paginated.map(s => (
                            <div key={s.id} style={{
                                background: 'white', borderRadius: 12, border: '1.5px solid #e2e8f0',
                                overflow: 'hidden', display: 'flex', flexDirection: 'column',
                                boxShadow: '0 2px 8px rgba(0,0,0,0.04)', transition: 'transform 0.2s, box-shadow 0.2s',
                                cursor: 'default'
                            }}
                                onMouseOver={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.08)'; }}
                                onMouseOut={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.04)'; }}
                            >
                                {/* Blue Header */}
                                <div style={{
                                    background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
                                    padding: '18px 16px 14px', display: 'flex', alignItems: 'flex-start', gap: 12
                                }}>
                                    <img src={s.icon} alt="" style={{ width: 28, height: 28, filter: 'brightness(10)', flexShrink: 0, marginTop: 2 }} onError={e => e.target.style.display = 'none'} />
                                    <div style={{ fontSize: 14, fontWeight: 800, color: 'white', lineHeight: 1.35 }}>
                                        {s.name}
                                    </div>
                                </div>

                                {/* Body */}
                                <div style={{ padding: '14px 16px 8px', flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    <p style={{ fontSize: 12.5, color: '#475569', lineHeight: 1.5, margin: 0, flex: 1 }}>
                                        {(s.description || '').substring(0, 120)}{(s.description || '').length > 120 ? '...' : ''}
                                    </p>
                                    <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.4 }}>
                                        <strong style={{ color: '#334155' }}>Eligibility:</strong>{' '}
                                        {(s.eligibility || '').substring(0, 100)}{(s.eligibility || '').length > 100 ? '...' : ''}
                                    </div>
                                </div>

                                {/* Footer: View Official Info Button */}
                                <div style={{ padding: '10px 16px 16px' }}>
                                    <button
                                        onClick={() => handleSchemeClick(s.name)}
                                        style={{
                                            width: '100%', padding: '10px 0', background: '#16a34a', color: 'white',
                                            borderRadius: 8, fontSize: 13, fontWeight: 700, border: 'none',
                                            cursor: 'pointer', display: 'flex', alignItems: 'center',
                                            justifyContent: 'center', gap: 6, transition: 'background 0.2s'
                                        }}
                                        onMouseOver={e => e.currentTarget.style.background = '#15803d'}
                                        onMouseOut={e => e.currentTarget.style.background = '#16a34a'}
                                    >
                                        <ExternalLink size={14} /> View Official Info
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Pagination */}
                    {totalPages > 1 && (
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 8, marginBottom: 40 }}>
                            <button
                                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                disabled={currentPage === 1}
                                style={{
                                    padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0',
                                    background: 'white', color: currentPage === 1 ? '#cbd5e1' : '#334155',
                                    cursor: currentPage === 1 ? 'default' : 'pointer', fontSize: 13, fontWeight: 600
                                }}
                            >← Back</button>

                            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                let pageNum;
                                if (totalPages <= 5) { pageNum = i + 1; }
                                else if (currentPage <= 3) { pageNum = i + 1; }
                                else if (currentPage >= totalPages - 2) { pageNum = totalPages - 4 + i; }
                                else { pageNum = currentPage - 2 + i; }
                                return (
                                    <button key={pageNum} onClick={() => setCurrentPage(pageNum)}
                                        style={{
                                            width: 36, height: 36, borderRadius: 8, fontSize: 13, fontWeight: 700,
                                            border: pageNum === currentPage ? '2px solid #2563eb' : '1px solid #e2e8f0',
                                            background: pageNum === currentPage ? '#2563eb' : 'white',
                                            color: pageNum === currentPage ? 'white' : '#64748b',
                                            cursor: 'pointer'
                                        }}
                                    >{pageNum}</button>
                                );
                            })}

                            {totalPages > 5 && <span style={{ color: '#94a3b8', fontSize: 14 }}>...</span>}
                            {totalPages > 5 && (
                                <button onClick={() => setCurrentPage(totalPages)}
                                    style={{
                                        width: 36, height: 36, borderRadius: 8, fontSize: 13, fontWeight: 700,
                                        border: currentPage === totalPages ? '2px solid #2563eb' : '1px solid #e2e8f0',
                                        background: currentPage === totalPages ? '#2563eb' : 'white',
                                        color: currentPage === totalPages ? 'white' : '#64748b', cursor: 'pointer'
                                    }}
                                >{totalPages}</button>
                            )}

                            <button
                                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                disabled={currentPage === totalPages}
                                style={{
                                    padding: '8px 16px', borderRadius: 8, border: '1px solid #e2e8f0',
                                    background: 'white', color: currentPage === totalPages ? '#cbd5e1' : '#334155',
                                    cursor: currentPage === totalPages ? 'default' : 'pointer', fontSize: 13, fontWeight: 600
                                }}
                            >Next →</button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default Schemes;
