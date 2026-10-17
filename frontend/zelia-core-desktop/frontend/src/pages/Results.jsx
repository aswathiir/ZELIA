import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { CheckCircle, XCircle, FileText, ArrowLeft, Download, Printer, Clock, MessageSquare } from 'lucide-react';

const Results = () => {
    const location = useLocation();
    const navigate = useNavigate();

    const result = location.state?.result || {};
    const statusText = result.status || 'Processed';
    const isPositive = !['No Match', 'Error', 'Failed'].includes(statusText);
    const requiredDocuments = Array.isArray(result.requiredDocuments) ? result.requiredDocuments : [];
    const missingRequiredDocuments = Array.isArray(result.missingRequiredDocuments) ? result.missingRequiredDocuments : [];
    const confidence = typeof result.confidence === 'number' ? result.confidence : (result.documentFilled ? 92 : 70);

    const confColor = confidence >= 80 ? 'var(--ok-text)' : confidence >= 65 ? 'var(--warn-text)' : 'var(--err-text)';
    const confBg = confidence >= 80 ? 'var(--ok-bg)' : confidence >= 65 ? 'var(--warn-bg)' : 'var(--err-bg)';

    return (
        <div style={{ maxWidth: 820, margin: '0 auto' }}>

            {/* Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 22 }}>
                <button onClick={() => navigate('/dashboard')} className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', fontSize: 13 }}>
                    <ArrowLeft size={16} /> Dashboard
                </button>
                <div style={{ display: 'flex', gap: 8 }}>
                    <button className="btn btn-outline" style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '8px 14px', fontSize: 13 }}>
                        <Printer size={15} /> Print
                    </button>
                    <button className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '8px 14px', fontSize: 13 }}
                        onClick={() => result.householdHash && navigate(`/citizen/documents?hash=${result.householdHash}`)}>
                        <Download size={15} /> Open Portal
                    </button>
                </div>
            </div>

            {/* Main report card */}
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>

                {/* Status banner */}
                <div style={{ padding: '30px 32px', textAlign: 'center', background: isPositive ? 'var(--ok-bg)' : 'var(--err-bg)', borderBottom: '1.5px solid var(--border)' }}>
                    <div style={{ width: 64, height: 64, margin: '0 auto 14px', borderRadius: '50%', background: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', color: isPositive ? 'var(--ok-text)' : 'var(--err-text)', boxShadow: '0 2px 8px rgba(6,14,31,.12)' }}>
                        {isPositive ? <CheckCircle size={32} /> : <XCircle size={32} />}
                    </div>
                    <h2 style={{ fontSize: 22, fontWeight: 900, color: 'var(--ink-900)', marginBottom: 6 }}>
                        {statusText}
                    </h2>
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        REF: {result.id || result.callId || 'N/A'}
                    </p>
                </div>

                {/* Details */}
                <div style={{ padding: 28 }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28, marginBottom: 24 }}>

                        {/* Beneficiary */}
                        <div>
                            <h3 style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: .7, color: 'var(--text-muted)', marginBottom: 14 }}>Beneficiary Details</h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                                {[
                                    ['Full Name', result.beneficiary || 'Citizen'],
                                    ['Best Matched Scheme', result.scheme || 'No exact scheme match'],
                                    ['Timestamp', result.timestamp || new Date().toLocaleString('en-IN')],
                                ].map(([label, val]) => (
                                    <div key={label}>
                                        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 3 }}>{label}</div>
                                        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)' }}>{val}</div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Analysis */}
                        <div>
                            <h3 style={{ fontSize: 11, fontWeight: 800, textTransform: 'uppercase', letterSpacing: .7, color: 'var(--text-muted)', marginBottom: 14 }}>Analysis Results</h3>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>

                                {/* Confidence score */}
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>AI Confidence Score</div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                                        <div style={{ flex: 1, height: 8, background: 'var(--ink-100)', borderRadius: 4, maxWidth: 140, overflow: 'hidden' }}>
                                            <div style={{ width: `${confidence}%`, height: '100%', background: 'var(--ink-700)', borderRadius: 4, transition: 'width .6s' }} />
                                        </div>
                                        <span style={{ fontSize: 14, fontWeight: 800, color: confColor, background: confBg, padding: '3px 10px', borderRadius: 20 }}>
                                            {confidence}%
                                        </span>
                                    </div>
                                </div>

                                {/* Questions */}
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 3 }}>Questions Covered</div>
                                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)', display: 'flex', alignItems: 'center', gap: 6 }}>
                                        <MessageSquare size={15} color="var(--ink-500)" /> {result.transcriptCount ?? result.questionsCovered ?? 0}
                                    </div>
                                </div>

                                {/* Duration */}
                                <div>
                                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 3 }}>Call Duration</div>
                                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--ink-900)', display: 'flex', alignItems: 'center', gap: 6 }}>
                                        <Clock size={15} color="var(--ink-500)" /> {result.duration || '00:00'}
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>

                    {/* Officer notes */}
                    <div style={{ padding: '16px 18px', background: 'var(--surface-alt)', border: '1.5px solid var(--border)', borderRadius: 10, marginBottom: 18 }}>
                        <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                            <FileText size={13} /> OFFICER NOTES
                        </div>
                        <div style={{ fontSize: 13, color: 'var(--ink-700)', lineHeight: 1.7 }}>
                            {result.responseText || `Automated processing completed. ${isPositive ? 'Proceed to document upload and CHW verification.' : 'No eligible scheme matched with current profile.'}`}
                        </div>
                    </div>

                    {/* Document Upload Link */}
                    {result.householdHash && (
                        <div style={{ padding: '24px 18px', background: 'var(--ok-bg)', border: '1.5px solid var(--ok-text)', borderRadius: 12, marginBottom: 18, textAlign: 'center' }}>
                            <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--ink-900)', marginBottom: 8 }}>
                                Next Step: Document Upload
                            </div>
                            <div style={{ fontSize: 14, color: 'var(--ink-700)', marginBottom: 20 }}>
                                Your profile is ready. Please proceed to upload your documents for automated verification. {requiredDocuments.length > 0 ? <div style={{ marginTop: 8, fontWeight: 700 }}>Required: {requiredDocuments.join(', ')}</div> : ''}
                            </div>
                            <button
                                onClick={() => navigate(`/citizen/documents?hash=${result.householdHash}`)}
                                className="btn btn-primary"
                                style={{ width: '100%', padding: '16px 24px', fontSize: 16, fontWeight: 900, justifyContent: 'center', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                            >
                                <FileText size={20} style={{ marginRight: 8 }} /> PROCEED TO UPLOAD PORTAL
                            </button>
                        </div>
                    )}

                    {(requiredDocuments.length > 0 || missingRequiredDocuments.length > 0) && (
                        <div style={{ padding: '16px 18px', background: 'var(--surface-alt)', border: '1.5px solid var(--border)', borderRadius: 10, marginBottom: 18 }}>
                            <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', marginBottom: 8 }}>DOCUMENT CHECKLIST</div>
                            <div style={{ fontSize: 13, color: 'var(--ink-700)' }}>
                                <div>Required: {requiredDocuments.length ? requiredDocuments.join(', ') : 'Not specified'}</div>
                                <div style={{ marginTop: 6 }}>Missing: {missingRequiredDocuments.length ? missingRequiredDocuments.join(', ') : 'None detected yet'}</div>
                                {result.storagePath && <div style={{ marginTop: 6, fontFamily: 'monospace', fontSize: 12 }}>Filled Form Path: {result.storagePath}</div>}
                            </div>
                        </div>
                    )}

                    {/* Action buttons */}
                    <div style={{ display: 'flex', gap: 12 }}>
                        <button onClick={() => navigate('/active-calls')} className="btn btn-outline" style={{ flex: 1, padding: 12, fontSize: 14, justifyContent: 'center' }}>
                            Back to Active Calls
                        </button>
                        <button onClick={() => navigate('/dashboard')} className="btn btn-primary" style={{ flex: 1, padding: 12, fontSize: 14, justifyContent: 'center' }}>
                            New Verification
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Results;
