import React from 'react';
import { useLanguage } from '../context/LanguageContext';

const ApplicationCard = ({ application }) => {
    const { language } = useLanguage();
    const hi = language === 'Hindi';

    if (!application) return null;

    const { id, name, scheme, date, status } = application;

    const badgeClass = {
        Approved: 'badge-success',
        Pending: 'badge-warning',
        Rejected: 'badge-error',
    }[status] || 'badge-gray';

    const badgeLabel = {
        Approved: hi ? '✓ स्वीकृत' : '✓ Approved',
        Pending: hi ? '⏳ लंबित' : '⏳ Pending',
        Rejected: hi ? '✕ अस्वीकृत' : '✕ Rejected',
    }[status] || status;

    return (
        <tr>
            <td>
                <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--text-muted)' }}>{id}</span>
            </td>
            <td>
                <span style={{ fontWeight: 700, color: 'var(--ink-900)' }}>{name}</span>
            </td>
            <td>{scheme}</td>
            <td style={{ color: 'var(--text-muted)' }}>{date}</td>
            <td>
                <span className={`badge ${badgeClass}`}>{badgeLabel}</span>
            </td>
        </tr>
    );
};

export default ApplicationCard;
