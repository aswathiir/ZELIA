import React from 'react';
import { FileText, Check, AlertTriangle, X, ExternalLink, Share2 } from 'lucide-react';

const DocumentCard = ({ document }) => {
    const { type, status, extractedData } = document;

    const getStatusIcon = (status) => {
        switch (status.toLowerCase()) {
            case 'valid': return <Check size={16} className="text-success" />;
            case 'warning': return <AlertTriangle size={16} className="text-warning" />;
            case 'invalid': return <X size={16} className="text-error" />;
            default: return null;
        }
    };

    const getStatusColor = (status) => {
        switch (status.toLowerCase()) {
            case 'valid': return 'bg-success-bg text-success border-success/20';
            case 'warning': return 'bg-warning-bg text-warning border-warning/20';
            case 'invalid': return 'bg-error-bg text-error border-error/20';
            default: return 'bg-neutral-200 text-neutral-600';
        }
    };

    return (
        <div className="card p-0 overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b border-border-color bg-neutral-200/50 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-white rounded-lg border border-border-color text-primary">
                        <FileText size={20} />
                    </div>
                    <div>
                        <h4 className="font-medium text-main">{type}</h4>
                        <div className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border mt-1 ${getStatusColor(status)}`}>
                            {getStatusIcon(status)}
                            <span className="capitalize">{status}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Body */}
            <div className="p-4">
                <h5 className="text-xs font-semibold text-secondary uppercase tracking-wider mb-3">Extracted Data</h5>
                <div className="space-y-2">
                    {Object.entries(extractedData).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm border-b border-dashed border-border-color pb-1 last:border-0">
                            <span className="text-secondary">{key}:</span>
                            <span className="font-medium text-main text-right">{value}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer Actions */}
            <div className="bg-neutral-200/30 p-2 flex gap-2 border-t border-border-color">
                <button className="flex-1 btn btn-outline text-xs py-1.5 h-8">
                    <ExternalLink size={14} /> View Image
                </button>
                <button className="btn btn-outline text-xs py-1.5 px-2 h-8">
                    <Share2 size={14} />
                </button>
            </div>
        </div>
    );
};

export default DocumentCard;
