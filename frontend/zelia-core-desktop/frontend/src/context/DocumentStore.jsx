/**
 * DocumentStore.jsx
 * Shared in-memory document store for the demo.
 * In production this would be replaced with API calls.
 */
import React, { createContext, useContext, useState } from 'react';

/* Document type catalogue */
export const DOC_TYPES = [
    { id: 'aadhaar', label: 'Aadhaar Card', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'pan', label: 'PAN Card', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'income', label: 'Income Certificate', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'caste', label: 'Caste Certificate', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'bank', label: 'Bank Passbook', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'photo', label: 'Passport Photo', accepted: '.jpg,.jpeg,.png' },
    { id: 'residence', label: 'Residence Proof', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'land', label: 'Land Records', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'disability', label: 'Disability Certificate', accepted: '.pdf,.jpg,.jpeg,.png' },
    { id: 'birth', label: 'Birth Certificate', accepted: '.pdf,.jpg,.jpeg,.png' },
];

/* Seed data — demo documents for the logged-in citizen (Rajesh Kumar) */
const SEED_DOCS = {
    'citizen-001': {
        userId: 'citizen-001',
        userName: 'Rajesh Kumar',
        aadhaar: 'XXXX XXXX 4210',
        docs: [
            { id: 'd1', typeId: 'aadhaar', name: 'Aadhaar_RajeshKumar.pdf', size: 210_000, uploadedAt: '2024-10-05', status: 'verified' },
            { id: 'd2', typeId: 'income', name: 'Income_Certificate.pdf', size: 145_000, uploadedAt: '2024-10-05', status: 'verified' },
            { id: 'd3', typeId: 'bank', name: 'Bank_Passbook_SBI.jpg', size: 320_000, uploadedAt: '2024-10-06', status: 'pending' },
            { id: 'd4', typeId: 'photo', name: 'Passport_Photo.jpg', size: 85_000, uploadedAt: '2024-10-06', status: 'verified' },
        ],
    },
    'citizen-002': {
        userId: 'citizen-002',
        userName: 'Priya Singh',
        aadhaar: 'XXXX XXXX 9012',
        docs: [
            { id: 'd5', typeId: 'aadhaar', name: 'Aadhaar_PriyaSingh.pdf', size: 198_000, uploadedAt: '2024-10-10', status: 'verified' },
            { id: 'd6', typeId: 'caste', name: 'Caste_Certificate.pdf', size: 230_000, uploadedAt: '2024-10-11', status: 'pending' },
        ],
    },
    'citizen-003': {
        userId: 'citizen-003',
        userName: 'Anil Patel',
        aadhaar: 'XXXX XXXX 3344',
        docs: [
            { id: 'd7', typeId: 'aadhaar', name: 'Aadhaar_AnilPatel.pdf', size: 211_000, uploadedAt: '2024-10-12', status: 'verified' },
            { id: 'd8', typeId: 'income', name: 'Income_Certificate.pdf', size: 155_000, uploadedAt: '2024-10-12', status: 'rejected' },
            { id: 'd9', typeId: 'bank', name: 'Bank_Passbook.pdf', size: 290_000, uploadedAt: '2024-10-13', status: 'pending' },
        ],
    },
    'citizen-004': {
        userId: 'citizen-004',
        userName: 'Sunita Devi',
        aadhaar: 'XXXX XXXX 7788',
        docs: [
            { id: 'd10', typeId: 'aadhaar', name: 'Aadhaar_SunitaDevi.pdf', size: 205_000, uploadedAt: '2024-11-01', status: 'verified' },
            { id: 'd11', typeId: 'income', name: 'Income_Cert.pdf', size: 160_000, uploadedAt: '2024-11-01', status: 'verified' },
            { id: 'd12', typeId: 'land', name: 'Land_Records.pdf', size: 410_000, uploadedAt: '2024-11-02', status: 'verified' },
            { id: 'd13', typeId: 'bank', name: 'Bank_Passbook.jpg', size: 275_000, uploadedAt: '2024-11-02', status: 'pending' },
            { id: 'd14', typeId: 'photo', name: 'Photo.jpg', size: 78_000, uploadedAt: '2024-11-02', status: 'verified' },
        ],
    },
};

const DocCtx = createContext(null);

export const DocumentProvider = ({ children }) => {
    const [store, setStore] = useState(SEED_DOCS);

    /* citizen adds a new doc */
    const addDoc = (userId, file, typeId, storagePath = null) => {
        const objectUrl = URL.createObjectURL(file);   // live blob URL for this session
        const newDoc = {
            id: 'D' + Date.now(),
            typeId,
            name: file.name,
            size: file.size,
            uploadedAt: new Date().toISOString().slice(0, 10),
            status: 'pending',
            objectUrl,                                 // stored so both views can open it
            storagePath,                               // actual path in MinIO
        };
        setStore(prev => ({
            ...prev,
            [userId]: {
                ...prev[userId],
                docs: [...(prev[userId]?.docs ?? []), newDoc],
            },
        }));
    };

    /* officer changes status */
    const setDocStatus = (userId, docId, status) => {
        setStore(prev => ({
            ...prev,
            [userId]: {
                ...prev[userId],
                docs: prev[userId].docs.map(d => d.id === docId ? { ...d, status } : d),
            },
        }));
    };

    /* delete a doc */
    const removeDoc = (userId, docId) => {
        setStore(prev => ({
            ...prev,
            [userId]: {
                ...prev[userId],
                docs: prev[userId].docs.filter(d => d.id !== docId),
            },
        }));
    };

    return (
        <DocCtx.Provider value={{ store, addDoc, setDocStatus, removeDoc }}>
            {children}
        </DocCtx.Provider>
    );
};

export const useDocuments = () => useContext(DocCtx);

export const fmtSize = (bytes) => {
    if (bytes >= 1_000_000) return (bytes / 1_000_000).toFixed(1) + ' MB';
    return Math.round(bytes / 1000) + ' KB';
};
