import React from 'react';
import { CheckCircle, Clock, XCircle, AlertTriangle } from 'lucide-react';

const StatusBadge = ({ status, confidence }) => {
    const normalizedStatus = status?.toLowerCase() || 'pending';

    let config = {
        class: 'badge-warning',
        icon: <Clock size={12} />,
        label: 'Pending'
    };

    if (normalizedStatus.includes('approved') || normalizedStatus.includes('valid')) {
        config = {
            class: 'badge-success',
            icon: <CheckCircle size={12} />,
            label: 'Approved'
        };
    } else if (normalizedStatus.includes('rejected') || normalizedStatus.includes('invalid')) {
        config = {
            class: 'badge-error',
            icon: <XCircle size={12} />,
            label: 'Rejected'
        };
    }

    return (
        <span className={`status-badge ${config.class}`}>
            {config.icon}
            {config.label}
            {confidence && <span style={{ opacity: 0.8, marginLeft: '4px' }}>{confidence}%</span>}
        </span>
    );
};

export default StatusBadge;
