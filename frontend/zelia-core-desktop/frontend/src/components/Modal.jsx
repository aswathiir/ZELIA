import React from 'react';
import { X } from 'lucide-react';

const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-box" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">{title}</h2>
                    <button onClick={onClose}
                        style={{ padding: 6, borderRadius: 6, color: 'var(--ink-500)', transition: 'background .15s' }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--ink-100)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                        <X size={18} />
                    </button>
                </div>
                <div className="modal-body">{children}</div>
            </div>
        </div>
    );
};

export default Modal;
