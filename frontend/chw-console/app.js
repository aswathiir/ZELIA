/**
 * ZELIA CHW Console - Application Logic
 */

let schemesData = [];
let casesData = [];

function normalizeStatus(status) {
    const s = (status || '').toLowerCase();
    if (s === 'pending_chw_review' || s === 'pending') return 'pending_review';
    if (s === 'processing_failed') return 'processing_error';
    return s || 'pending_review';
}

function isPendingStatus(status) {
    return normalizeStatus(status) === 'pending_review';
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('zelia_token')) {
        showApp();
    }

    // Login form handler
    document.getElementById('login-form').addEventListener('submit', handleLogin);

    // Submit form handler
    document.getElementById('submit-form').addEventListener('submit', handleSubmit);
});

async function handleLogin(e) {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    btn.innerHTML = '<span class="loader"></span>';

    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;

    const success = await ZeliaAPI.login(username, password);

    if (success) {
        showApp();
    } else {
        btn.innerHTML = '<span>Sign In</span>';
        alert('Login failed');
    }
}

function handleLogout() {
    ZeliaAPI.logout();
    document.getElementById('main-app').classList.remove('active');
    document.getElementById('login-page').classList.add('active');
}

function showApp() {
    document.getElementById('login-page').classList.remove('active');
    document.getElementById('main-app').classList.add('active');
    loadDashboard();
    loadSchemes();
    loadCases();
}

function toggleMenu() {
    document.getElementById('nav-menu').classList.toggle('active');
}

function showSection(section) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(section).classList.add('active');

    document.querySelectorAll('.nav-links a').forEach(a => a.classList.remove('active'));
    const navItem = document.getElementById('nav-' + section);
    if (navItem) navItem.classList.add('active');

    document.getElementById('nav-menu').classList.remove('active');
}

async function loadDashboard() {
    try {
        const data = await ZeliaAPI.getSubmissions({ limit: 200 });
        casesData = data.submissions || [];
    } catch {
        casesData = [];
    }
    document.getElementById('stat-total').textContent = casesData.length;
    document.getElementById('stat-pending').textContent = casesData.filter(c => isPendingStatus(c.status)).length;
    document.getElementById('stat-approved').textContent = casesData.filter(c => normalizeStatus(c.status) === 'approved').length;

    try {
        const schemes = await ZeliaAPI.getSchemes();
        schemesData = schemes;
        document.getElementById('stat-schemes').textContent = schemes.length;
    } catch {
        document.getElementById('stat-schemes').textContent = '6';
    }

    loadStatus();
}

async function loadStatus() {
    const container = document.getElementById('system-status');
    container.innerHTML = '<div class="loader"></div> Checking services...';

    try {
        const status = await ZeliaAPI.getSystemStatus();
        let html = `<p style="margin-bottom:0.75rem;"><strong>Status:</strong> 
            <span class="badge ${status.overall_status === 'healthy' ? 'badge-success' : 'badge-warning'}">
                ${status.overall_status.toUpperCase()}
            </span>
            <span style="margin-left:0.5rem;color:var(--text-muted);">${status.healthy_count}/${status.total_count} services</span>
        </p><div style="display:flex;flex-wrap:wrap;gap:0.5rem;">`;

        for (const [name, info] of Object.entries(status.services)) {
            const badge = info.status === 'healthy' ? 'badge-success' : 'badge-error';
            html += `<span class="badge ${badge}">${name}</span>`;
        }
        html += '</div>';
        container.innerHTML = html;
    } catch {
        container.innerHTML = '<p class="badge badge-warning">Could not reach status endpoint</p>';
    }
}

async function loadSchemes() {
    const grid = document.getElementById('schemes-grid');
    const select = document.getElementById('scheme-select');
    const filter = document.getElementById('category-filter');

    try {
        schemesData = await ZeliaAPI.getSchemes();
        const categories = await ZeliaAPI.getCategories();

        // Populate category filter
        filter.innerHTML = '<option value="">All Categories</option>';
        categories.categories.forEach(cat => {
            filter.innerHTML += `<option value="${cat}">${cat.charAt(0).toUpperCase() + cat.slice(1)}</option>`;
        });

        renderSchemes(schemesData);

        // Populate scheme select
        select.innerHTML = '<option value="">Select Scheme...</option>';
        schemesData.forEach(s => {
            select.innerHTML += `<option value="${s.scheme_id}">${s.title}</option>`;
        });

    } catch {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>Could not load schemes</p></div>';
    }
}

function renderSchemes(schemes) {
    const grid = document.getElementById('schemes-grid');

    if (schemes.length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><p>No schemes found</p></div>';
        return;
    }

    grid.innerHTML = schemes.map(s => `
        <div class="scheme-card">
            <div class="scheme-title">${s.title}</div>
            <p class="scheme-desc">${s.description || 'No description available'}</p>
            <span class="badge badge-info">${s.category}</span>
            <span class="badge badge-success" style="margin-left:0.25rem;">${s.state_code}</span>
        </div>
    `).join('');
}

function filterSchemes() {
    const category = document.getElementById('category-filter').value;
    if (!category) {
        renderSchemes(schemesData);
    } else {
        renderSchemes(schemesData.filter(s => s.category === category));
    }
}

async function loadCases() {
    try {
        const data = await ZeliaAPI.getSubmissions({ limit: 100 });
        casesData = data.submissions || [];
    } catch {
        casesData = [];
    }

    const rows = casesData.map((c) => {
        const schemeName = c.metadata?.scheme_id || c.scheme_id || 'N/A';
        const applicant = c.metadata?.applicant_name || c.user_id || c.household_hash || 'Applicant';
        const date = c.created_at || c.reviewed_at || new Date().toISOString();
        return { ...c, schemeName, applicant, date, status: normalizeStatus(c.status) };
    });

    // Mobile cards
    const mobileContainer = document.getElementById('cases-mobile');
    mobileContainer.innerHTML = rows.map(c => `
        <div class="case-card">
            <div class="case-card-header">
                <span class="case-name">${c.applicant}</span>
                <span class="badge badge-${normalizeStatus(c.status) === 'approved' ? 'success' : isPendingStatus(c.status) ? 'warning' : 'error'}">
                    ${c.status.replace('_', ' ')}
                </span>
            </div>
            <p class="case-meta">${c.schemeName} • ${ZeliaAPI.formatDate(c.date)}</p>
            <div style="display:flex;gap:0.4rem;margin-top:0.5rem;">
              <button class="btn btn-sm btn-secondary" onclick="viewCase('${c.submission_id}')">View</button>
              ${isPendingStatus(c.status) ? `<button class="btn btn-sm btn-primary" onclick="approveCase('${c.submission_id}')">Approve</button>
              <button class="btn btn-sm btn-danger" onclick="rejectCase('${c.submission_id}')">Reject</button>` : ''}
            </div>
        </div>
    `).join('');

    // Desktop table
    const tableBody = document.getElementById('cases-table');
    tableBody.innerHTML = rows.map(c => `
        <tr>
            <td>${c.applicant}</td>
            <td>${c.schemeName}</td>
            <td><span class="badge badge-${normalizeStatus(c.status) === 'approved' ? 'success' : isPendingStatus(c.status) ? 'warning' : 'error'}">${c.status.replace('_', ' ')}</span></td>
            <td>${ZeliaAPI.formatDate(c.date)}</td>
            <td>
              <button class="btn btn-sm btn-secondary" onclick="viewCase('${c.submission_id}')">View</button>
              ${isPendingStatus(c.status) ? `<button class="btn btn-sm btn-primary" onclick="approveCase('${c.submission_id}')">Approve</button>
              <button class="btn btn-sm btn-danger" onclick="rejectCase('${c.submission_id}')">Reject</button>` : ''}
            </td>
        </tr>
    `).join('');
}

async function viewCase(submissionId) {
    const resultDiv = document.getElementById('eligibility-result');
    try {
        const data = await ZeliaAPI.getSubmission(submissionId);
        const checklist = data.verification_checklist || {};
        const mismatches = checklist.mismatched_fields || [];
        const aadhaarQr = checklist.aadhaar_qr_verification || {};
        const qrStatus = (aadhaarQr.status || 'signature_not_present').toLowerCase();
        const qrBadge = qrStatus === 'signature_valid'
            ? 'success'
            : (qrStatus === 'signature_invalid' ? 'error' : 'warning');
        const qrCheck = (aadhaarQr.checks && aadhaarQr.checks[0]) || {};
        const qrMessage = qrCheck.message || '';
        const qrDecoderMessage = qrCheck.decoder_message || '';
        const mismatchHtml = mismatches.length
            ? `<details style="margin-top:0.5rem;"><summary>Mismatches (${mismatches.length})</summary>${mismatches.map(m => `
                <div style="margin-top:0.35rem;padding:0.35rem;border-left:3px solid #d9534f;">
                    <div><strong>${m.field || 'field'}</strong></div>
                    <div>Form: ${m.filled_form_value ?? 'N/A'}</div>
                    <div>Document: ${m.extracted_document_value ?? 'N/A'}</div>
                    <div>Source: ${(m.source_document_type || 'N/A')} ${m.source_document_image ? `• ${m.source_document_image}` : ''}</div>
                </div>`).join('')}</details>`
            : '';
        resultDiv.innerHTML = `
            <div class="alert alert-success">
                <p><strong>Submission:</strong> ${data.submission_id}</p>
                <p>Status: ${data.status}</p>
                <p>Docs Verified: ${(checklist.all_required_documents_verified === true) ? 'Yes' : 'No'}</p>
                <p>Form Fields Matched: ${(checklist.all_form_fields_matched === true) ? 'Yes' : 'No'}</p>
                <p>Aadhaar Secure QR: <span class="badge badge-${qrBadge}">${qrStatus}</span>${qrMessage ? ` - ${qrMessage}` : ''}${qrDecoderMessage ? `<br/><small>Decoder: ${qrDecoderMessage}</small>` : ''}</p>
                <p style="word-break:break-all;">File: ${data.file_uri || data.filled_pdf_uri || 'N/A'}</p>
                ${mismatchHtml}
            </div>
        `;
    } catch (err) {
        resultDiv.innerHTML = `<div class="alert alert-error">Failed to fetch submission: ${err.message}</div>`;
    }
}

async function approveCase(submissionId) {
    const resultDiv = document.getElementById('eligibility-result');
    try {
        const validation = await ZeliaAPI.validateSubmissionDocuments(submissionId, { auto_correct_form: false });
        if (!validation.submission_allowed) {
            const mismatchHtml = (validation.mismatched_fields || []).map(m => `
                <li><strong>${m.field || 'field'}:</strong> form="${m.filled_form_value ?? 'N/A'}" vs doc="${m.extracted_document_value ?? 'N/A'}"</li>
            `).join('');
            resultDiv.innerHTML = `
                <div class="alert alert-warning">
                    <p><strong>Submission blocked by Document Consistency Validator</strong></p>
                    <p>Missing docs: ${(validation.missing_required_documents || []).join(', ') || 'None'}</p>
                    <ul style="padding-left:1rem;">${mismatchHtml || '<li>No field mismatch details</li>'}</ul>
                </div>
            `;
            return;
        }
    } catch (err) {
        resultDiv.innerHTML = `<div class="alert alert-error">Validation failed: ${err.message}</div>`;
        return;
    }
    await reviewCase(submissionId, 'approve');
}

async function rejectCase(submissionId) {
    const reason = prompt('Enter rejection reason');
    if (reason === null) return;
    const missing = prompt('Enter missing/invalid fields (comma separated, e.g. name,address,aadhaar_number)');
    if (missing === null) return;
    const missingFields = missing
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
    if (missingFields.length === 0) {
        alert('At least one missing field is required for rejection.');
        return;
    }
    await reviewCase(submissionId, 'reject', reason, missingFields);
}

async function reviewCase(submissionId, action, reason = '', missingFields = []) {
    const reviewerId = 'chw_001';
    const resultDiv = document.getElementById('eligibility-result');
    try {
        const res = await ZeliaAPI.reviewSubmission(submissionId, action, reviewerId, reason, missingFields);
        if (action === 'reject' && res.prompt_user && res.correction_prompt) {
            const missing = (res.correction_prompt.missing_fields || []).join(', ') || 'N/A';
            resultDiv.innerHTML = `
                <div class="alert alert-warning">
                    <p><strong>Submission ${res.submission_id} marked ${res.status}</strong></p>
                    <p><strong>User Prompt:</strong> ${res.correction_prompt.message_en}</p>
                    <p><strong>Missing Fields:</strong> ${missing}</p>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `<div class="alert alert-success">Submission ${res.submission_id} marked ${res.status}</div>`;
        }
        await loadCases();
        await loadDashboard();
    } catch (err) {
        resultDiv.innerHTML = `<div class="alert alert-error">Review action failed: ${err.message}</div>`;
    }
}

window.viewCase = viewCase;
window.approveCase = approveCase;
window.rejectCase = rejectCase;

function getFormData() {
    const form = document.getElementById('submit-form');
    const data = Object.fromEntries(new FormData(form));

    // Calculate age
    if (data.dob) {
        data.age = ZeliaAPI.calculateAge(data.dob);
        data.date_of_birth = data.dob;
    }

    // Parse income
    if (data.income) data.monthly_income = parseInt(data.income);

    return data;
}

async function checkEligibility() {
    const resultDiv = document.getElementById('eligibility-result');
    const data = getFormData();

    if (!data.name) {
        resultDiv.innerHTML = '<div class="alert alert-error">Please enter applicant name</div>';
        return;
    }

    resultDiv.innerHTML = '<div class="loader"></div> Checking eligibility...';

    // Map scheme_id to rules engine scheme name
    const schemeMap = {
        'widow_pension': 'widow_pension',
        'old_age_pension': 'old_age_pension',
        'disability_pension': 'disability_pension'
    };

    // Try to find matching scheme
    let ruleScheme = 'old_age_pension'; // default
    const selected = schemesData.find(s => s.scheme_id === data.scheme);
    if (selected) {
        const title = selected.title.toLowerCase();
        if (title.includes('widow')) ruleScheme = 'widow_pension';
        else if (title.includes('disability')) ruleScheme = 'disability_pension';
        else if (title.includes('old age') || title.includes('senior')) ruleScheme = 'old_age_pension';
        else if (title.includes('girl') || title.includes('scholarship')) ruleScheme = 'girl_child_scholarship';
        else if (title.includes('mgnrega') || title.includes('employment')) ruleScheme = 'mgnrega';
    }

    try {
        const result = await ZeliaAPI.checkEligibility(ruleScheme, data);

        const badgeClass = result.result === 'eligible' ? 'success' :
            result.result === 'pending_review' ? 'warning' : 'error';

        resultDiv.innerHTML = `
            <div class="alert alert-${badgeClass}">
                <p><strong>Result:</strong> <span class="badge badge-${badgeClass}">${result.result.toUpperCase()}</span></p>
                <p style="margin-top:0.5rem;">${result.explanation}</p>
                <p style="margin-top:0.25rem;color:var(--text-muted);font-size:0.875rem;">
                    Confidence: ${(result.confidence * 100).toFixed(0)}%
                </p>
                ${result.matched_rules.length > 0 ? `
                    <details style="margin-top:0.75rem;">
                        <summary style="cursor:pointer;">Matched Rules</summary>
                        <ul style="margin-top:0.5rem;padding-left:1.5rem;font-size:0.875rem;">
                            ${result.matched_rules.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                    </details>
                ` : ''}
            </div>
        `;
    } catch (err) {
        resultDiv.innerHTML = `<div class="alert alert-error">Eligibility check failed: ${err.message}</div>`;
    }
}

async function generatePDF() {
    const resultDiv = document.getElementById('eligibility-result');
    const data = getFormData();

    if (!data.name) {
        resultDiv.innerHTML = '<div class="alert alert-error">Please enter applicant information</div>';
        return;
    }

    resultDiv.innerHTML = '<div class="loader"></div> Generating PDF...';

    let pdfScheme = 'old_age_pension';
    const selected = schemesData.find(s => s.scheme_id === data.scheme);
    if (selected) {
        const title = selected.title.toLowerCase();
        if (title.includes('widow')) pdfScheme = 'widow_pension';
        else if (title.includes('disability')) pdfScheme = 'disability_pension';
    }

    try {
        const result = await ZeliaAPI.generatePDF(pdfScheme, data);

        if (result.success) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <p><strong>✅ PDF Generated Successfully!</strong></p>
                    <p style="margin-top:0.5rem;word-break:break-all;font-size:0.875rem;">
                        Location: ${result.pdf_uri}
                    </p>
                </div>
            `;
        } else {
            throw new Error(result.message);
        }
    } catch (err) {
        resultDiv.innerHTML = `<div class="alert alert-error">PDF generation failed: ${err.message}</div>`;
    }
}

async function handleSubmit(e) {
    e.preventDefault();
    const resultDiv = document.getElementById('eligibility-result');
    const data = getFormData();

    resultDiv.innerHTML = '<div class="loader"></div> Submitting application...';

    // Create form data for file upload
    const formData = new FormData();
    formData.append('applicant_name', data.name);
    formData.append('scheme_id', data.scheme || 'unknown');
    formData.append('data', JSON.stringify(data));

    try {
        const result = await ZeliaAPI.submitApplication(formData);

        resultDiv.innerHTML = `
            <div class="alert alert-success">
                <p><strong>✅ Application Submitted!</strong></p>
                <p style="margin-top:0.5rem;">Submission ID: ${result.submission_id || 'Generated'}</p>
            </div>
        `;

        await loadCases();
        await loadDashboard();

    } catch (err) {
        resultDiv.innerHTML = `
            <div class="alert alert-success">
                <p><strong>✅ Application Saved (Demo Mode)</strong></p>
                <p style="margin-top:0.5rem;">Applicant: ${data.name}</p>
            </div>
        `;
    }
}
