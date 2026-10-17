/**
 * ZELIA CHW Console - API Integration
 */

const API = {
    gateway: 'http://localhost:8000',
    rules: 'http://localhost:8005',
    pdf: 'http://localhost:8006',
    submission: 'http://localhost:8009'
};

let authToken = localStorage.getItem('zelia_token');
let currentRole = localStorage.getItem('zelia_role') || 'chw';

// API Helper
async function apiCall(url, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    headers['X-User-Role'] = options.role || currentRole;

    try {
        const resp = await fetch(url, { ...options, headers });
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        return await resp.json();
    } catch (err) {
        console.error(`API Error: ${url}`, err);
        throw err;
    }
}

// Auth
async function login(username, password) {
    try {
        const data = await apiCall(`${API.gateway}/auth/login`, {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        authToken = data.access_token;
        localStorage.setItem('zelia_token', authToken);
        return true;
    } catch (err) {
        // Demo mode fallback
        authToken = 'demo-token';
        localStorage.setItem('zelia_token', authToken);
        return true;
    }
}

function logout() {
    authToken = null;
    localStorage.removeItem('zelia_token');
}

// Schemes
async function getSchemes(filters = {}) {
    let url = `${API.gateway}/schemes/`;
    const params = new URLSearchParams(filters);
    if (params.toString()) url += `?${params}`;
    return await apiCall(url);
}

async function getScheme(id) {
    return await apiCall(`${API.gateway}/schemes/${id}`);
}

async function getCategories() {
    return await apiCall(`${API.gateway}/schemes/categories/list`);
}

// Rules Engine
async function checkEligibility(schemeId, applicantData) {
    return await apiCall(`${API.rules}/check-eligibility`, {
        method: 'POST',
        body: JSON.stringify({
            scheme_id: schemeId,
            applicant_data: applicantData
        })
    });
}

async function getSchemeRules(schemeId) {
    return await apiCall(`${API.rules}/schemes/${schemeId}/rules`);
}

// PDF Service
async function generatePDF(schemeId, applicantData) {
    return await apiCall(`${API.pdf}/generate-and-store`, {
        method: 'POST',
        body: JSON.stringify({
            scheme_id: schemeId,
            applicant_data: applicantData
        })
    });
}

async function getPDFTemplates() {
    return await apiCall(`${API.pdf}/templates`);
}

// Submission
async function submitApplication(formData) {
    const headers = { 'X-User-Role': currentRole };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

    const resp = await fetch(`${API.submission}/sync`, {
        method: 'POST',
        headers,
        body: formData
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
}

async function getSubmissions(filters = {}) {
    let url = `${API.submission}/submissions`;
    const params = new URLSearchParams(filters);
    if (params.toString()) url += `?${params}`;
    return await apiCall(url);
}

async function getSubmission(submissionId) {
    return await apiCall(`${API.submission}/submissions/${submissionId}`);
}

async function reviewSubmission(submissionId, action, reviewerId, reason = '', missingFields = []) {
    return await apiCall(`${API.submission}/submissions/${submissionId}/review`, {
        method: 'POST',
        body: JSON.stringify({
            action,
            reviewer_id: reviewerId,
            reason,
            missing_fields: missingFields
        })
    });
}

async function validateSubmissionDocuments(submissionId, payload = {}) {
    return await apiCall(`${API.submission}/submissions/${submissionId}/validate-documents`, {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

async function verifyAadhaarQR(qrPayload, qrSignature) {
    return await apiCall(`${API.submission}/aadhaar/verify-qr`, {
        method: 'POST',
        body: JSON.stringify({
            qr_payload: qrPayload,
            qr_signature: qrSignature
        })
    });
}

async function decodeAadhaarQR(rawImageUri) {
    return await apiCall(`${API.submission}/aadhaar/decode-qr`, {
        method: 'POST',
        body: JSON.stringify({
            raw_image_uri: rawImageUri
        })
    });
}

async function submitCorrection(submissionId, actorId, correctedFields, note = '') {
    return await apiCall(`${API.submission}/submissions/${submissionId}/correction`, {
        method: 'POST',
        body: JSON.stringify({
            actor_id: actorId,
            corrected_fields: correctedFields,
            note
        }),
        role: 'citizen'
    });
}

async function getCorrectionPrompt(submissionId) {
    return await apiCall(`${API.submission}/submissions/${submissionId}/correction-prompt`, {
        role: 'citizen'
    });
}

// Status
async function getSystemStatus() {
    return await apiCall(`${API.gateway}/status/`);
}

// Helper: Calculate age from DOB
function calculateAge(dob) {
    const birth = new Date(dob);
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const m = today.getMonth() - birth.getMonth();
    if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) age--;
    return age;
}

// Helper: Format date
function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric'
    });
}

// Export for use
window.ZeliaAPI = {
    login, logout, getSchemes, getScheme, getCategories,
    checkEligibility, getSchemeRules, generatePDF, getPDFTemplates,
    submitApplication, getSubmissions, getSubmission, reviewSubmission, validateSubmissionDocuments, verifyAadhaarQR, decodeAadhaarQR, submitCorrection, getCorrectionPrompt,
    getSystemStatus, calculateAge, formatDate
};
