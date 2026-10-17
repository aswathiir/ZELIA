import React, { useState } from 'react';
import { Search } from 'lucide-react';

const HISTORY = [
    { id: 'APP-001', name: 'Rajesh Kumar', scheme: 'PM-JAY', date: '24 Feb 2026', time: '10:30', status: 'Approved', duration: '08:12' },
    { id: 'APP-002', name: 'Priya Singh', scheme: 'NREGA', date: '23 Feb 2026', time: '14:15', status: 'Pending', duration: '05:44' },
    { id: 'APP-003', name: 'Anil Patel', scheme: 'Pension', date: '22 Feb 2026', time: '09:02', status: 'Rejected', duration: '03:21' },
    { id: 'APP-004', name: 'Sunita Devi', scheme: 'PM Awas', date: '22 Feb 2026', time: '11:47', status: 'Approved', duration: '10:05' },
    { id: 'APP-005', name: 'Mohan Lal', scheme: 'Kisan', date: '21 Feb 2026', time: '16:33', status: 'Approved', duration: '07:30' },
    { id: 'APP-006', name: 'Geeta Sharma', scheme: 'Scholarship', date: '20 Feb 2026', time: '13:10', status: 'Pending', duration: '06:18' },
];

const STATUSES = ['All', 'Approved', 'Pending', 'Rejected'];

const History = () => {
    const [query, setQuery] = useState('');
    const [filter, setFilter] = useState('All');

    const rows = HISTORY.filter(r =>
        (filter === 'All' || r.status === filter) &&
        (r.name.toLowerCase().includes(query.toLowerCase()) || r.scheme.toLowerCase().includes(query.toLowerCase()))
    );

    const badgeClass = { Approved: 'badge-success', Pending: 'badge-warning', Rejected: 'badge-error' };

    return (
        <div>
            <div style={{ marginBottom: 24 }}>
                <h1 className="page-title">History</h1>
                <p className="page-subtitle">Past verifications and call records</p>
            </div>

            {/* Toolbar */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center' }}>
                <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
                    <Search size={15} style={{ position: 'absolute', left: 12, top: 13, color: 'var(--ink-400)' }} />
                    <input type="text" placeholder="Search name or scheme..."
                        value={query} onChange={e => setQuery(e.target.value)}
                        style={{ paddingLeft: 36, width: '100%' }} />
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                    {STATUSES.map(s => (
                        <button key={s} onClick={() => setFilter(s)}
                            style={{
                                padding: '9px 16px', borderRadius: 20, fontSize: 13, fontWeight: 700, cursor: 'pointer', fontFamily: 'inherit', border: '1.5px solid', transition: 'all .15s',
                                background: filter === s ? 'var(--ink-900)' : 'white',
                                color: filter === s ? 'white' : 'var(--ink-600)',
                                borderColor: filter === s ? 'var(--ink-900)' : 'var(--border)',
                            }}>
                            {s}
                        </button>
                    ))}
                </div>
            </div>

            {/* Table */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <table className="data-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Beneficiary</th>
                            <th>Scheme</th>
                            <th>Date</th>
                            <th>Duration</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.length === 0 ? (
                            <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>No records found.</td></tr>
                        ) : rows.map(r => (
                            <tr key={r.id}>
                                <td><span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>{r.id}</span></td>
                                <td><span style={{ fontWeight: 700 }}>{r.name}</span></td>
                                <td>{r.scheme}</td>
                                <td style={{ color: 'var(--text-muted)' }}>{r.date}<br /><span style={{ fontSize: 11 }}>{r.time}</span></td>
                                <td style={{ fontFamily: 'monospace', fontSize: 13 }}>{r.duration}</td>
                                <td><span className={`badge ${badgeClass[r.status]}`}>{r.status}</span></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <p style={{ marginTop: 12, fontSize: 12, color: 'var(--text-muted)' }}>{rows.length} record(s) found</p>
        </div>
    );
};

export default History;
