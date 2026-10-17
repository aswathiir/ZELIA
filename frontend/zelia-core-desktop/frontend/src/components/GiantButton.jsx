import React from 'react';
import { Loader } from 'lucide-react';

export const GiantButton = ({
    onClick,
    disabled,
    loading,
    icon: Icon,
    text,
    color = 'blue',
    fullWidth = true
}) => {

    const colors = {
        blue: { bg: '#0D1B33', active: '#060E1F', text: 'white' },
        green: { bg: '#1A5C3A', active: '#0D3820', text: 'white' },
        orange: { bg: '#D97706', active: '#92400E', text: 'white' }
    };

    const scheme = colors[color] || colors.blue;

    return (
        <button
            onClick={onClick}
            disabled={disabled || loading}
            style={{
                width: fullWidth ? '100%' : 'auto',
                minWidth: '60%',
                padding: '24px 32px',
                borderRadius: 24,
                border: 'none',
                background: scheme.bg,
                color: scheme.text,
                fontSize: 22,
                fontWeight: 900,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 16,
                cursor: (disabled || loading) ? 'not-allowed' : 'pointer',
                opacity: (disabled || loading) ? 0.6 : 1,
                boxShadow: '0 8px 16px rgba(0,0,0,0.1)',
                transition: 'all 0.2s',
                fontFamily: 'inherit'
            }}
            onMouseOver={(e) => {
                if (!disabled && !loading) e.currentTarget.style.background = scheme.active;
            }}
            onMouseOut={(e) => {
                if (!disabled && !loading) e.currentTarget.style.background = scheme.bg;
            }}
        >
            {loading ? <Loader size={28} style={{ animation: 'spin 1s linear infinite' }} /> : (Icon && <Icon size={28} />)}
            {text}
        </button>
    );
};
