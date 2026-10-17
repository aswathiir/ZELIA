// Fill ORIGINAL government template pages only (no appended summary page).
const { PDFDocument, StandardFonts } = require('pdf-lib');

function sanitize(text) {
  if (!text) return '';
  return String(text)
    .replace(/\u20b9/g, 'Rs.')
    .replace(/[\u0900-\u097F]/g, '')
    .replace(/[\u0B80-\u0BFF]/g, '')
    .replace(/[\u0C80-\u0CFF]/g, '')
    .replace(/[\u0D00-\u0D7F]/g, '')
    .replace(/[\u0C00-\u0C7F]/g, '')
    .replace(/[\u0A80-\u0AFF]/g, '')
    .replace(/[\u0A00-\u0A7F]/g, '')
    .replace(/[\u0980-\u09FF]/g, '')
    .replace(/[^\x20-\x7E\xA0-\xFF]/g, '')
    .trim();
}

function firstNodeJson(name) {
  try { return $(name).first().json; } catch (e) { return null; }
}

const fieldMap = {
  'Application_for_assiatance.pdf': { name: { page: 0, x: 404.75, y: 566.06, fontSize: 11.0 }, age: { page: 0, x: 404.75, y: 673.6, fontSize: 11.0 }, address: { page: 0, x: 404.75, y: 639.92, fontSize: 11.0 }, gender: { page: 0, x: 404.75, y: 606.24, fontSize: 11.0 } },
  'childofjail.pdf': { name: { page: 0, x: 402.45, y: 702.78, fontSize: 11.0 }, age: { page: 0, x: 402.45, y: 669.31, fontSize: 11.0 }, address: { page: 0, x: 402.45, y: 635.85, fontSize: 11.0 }, gender: { page: 0, x: 402.45, y: 602.38, fontSize: 11.0 } },
  'disabledgovt.pdf': { name: { page: 0, x: 404.82, y: 770.1, fontSize: 11.0 }, age: { page: 0, x: 404.82, y: 673.54, fontSize: 11.0 }, address: { page: 0, x: 404.82, y: 597.78, fontSize: 11.0 }, gender: { page: 0, x: 404.82, y: 606.18, fontSize: 11.0 } },
  'intimationform.pdf': { name: { page: 0, x: 404.82, y: 539.35, fontSize: 11.0 }, age: { page: 0, x: 404.82, y: 491.3, fontSize: 11.0 }, address: { page: 0, x: 404.82, y: 515.3, fontSize: 11.0 }, gender: { page: 0, x: 404.82, y: 606.18, fontSize: 11.0 } },
  'jobskilltraining.pdf': { name: { page: 0, x: 416.16, y: 665.28, fontSize: 11.0 }, age: { page: 0, x: 416.16, y: 633.6, fontSize: 11.0 }, address: { page: 0, x: 416.16, y: 601.92, fontSize: 11.0 }, gender: { page: 0, x: 416.16, y: 570.24, fontSize: 11.0 } },
  'mathrjyothi.pdf': { name: { page: 0, x: 416.16, y: 665.28, fontSize: 11.0 }, age: { page: 0, x: 416.16, y: 633.6, fontSize: 11.0 }, address: { page: 0, x: 416.16, y: 601.92, fontSize: 11.0 }, gender: { page: 0, x: 416.16, y: 570.24, fontSize: 11.0 } },
  'niramaya.pdf': { name: { page: 0, x: 416.16, y: 665.28, fontSize: 11.0 }, age: { page: 0, x: 416.16, y: 633.6, fontSize: 11.0 }, address: { page: 0, x: 416.16, y: 601.92, fontSize: 11.0 }, gender: { page: 0, x: 416.16, y: 570.24, fontSize: 11.0 } },
  'old_age_pension_karnataka.pdf': { name: { page: 0, x: 404.82, y: 707.52, fontSize: 11.0 }, age: { page: 0, x: 404.82, y: 694.86, fontSize: 11.0 }, address: { page: 0, x: 404.82, y: 682.14, fontSize: 11.0 }, gender: { page: 0, x: 404.82, y: 606.18, fontSize: 11.0 } },
  'pension1.pdf': { name: { page: 0, x: 380.0, y: 706.5, fontSize: 11.0 }, age: { page: 0, x: 480.0, y: 693.5, fontSize: 11.0 }, address: { page: 0, x: 380.0, y: 484.0, fontSize: 11.0 }, gender: { page: 0, x: 380.0, y: 656.5, fontSize: 11.0 } },
  'pmjay_enrollment.pdf': { name: { page: 0, x: 404.75, y: 566.06, fontSize: 11.0 }, age: { page: 0, x: 404.75, y: 673.6, fontSize: 11.0 }, address: { page: 0, x: 404.75, y: 639.92, fontSize: 11.0 }, gender: { page: 0, x: 404.75, y: 606.24, fontSize: 11.0 } },
  'pratibhaschem.pdf': { name: { page: 0, x: 404.6, y: 707.28, fontSize: 11.0 }, age: { page: 0, x: 404.6, y: 673.6, fontSize: 11.0 }, address: { page: 0, x: 404.6, y: 639.92, fontSize: 11.0 }, gender: { page: 0, x: 404.6, y: 606.24, fontSize: 11.0 } },
  'stateaward.pdf': { name: { page: 0, x: 404.74, y: 707.01, fontSize: 11.0 }, age: { page: 0, x: 404.74, y: 673.34, fontSize: 11.0 }, address: { page: 0, x: 404.74, y: 639.68, fontSize: 11.0 }, gender: { page: 0, x: 404.74, y: 606.01, fontSize: 11.0 } },
  'swasraya.pdf': { name: { page: 0, x: 404.82, y: 707.21, fontSize: 11.0 }, age: { page: 0, x: 404.82, y: 673.54, fontSize: 11.0 }, address: { page: 0, x: 404.82, y: 639.86, fontSize: 11.0 }, gender: { page: 0, x: 404.82, y: 606.18, fontSize: 11.0 } },
  'tamiltraining.pdf': { name: { page: 0, x: 416.16, y: 496.74, fontSize: 11.0 }, age: { page: 0, x: 416.16, y: 633.6, fontSize: 11.0 }, address: { page: 0, x: 416.16, y: 244.38, fontSize: 11.0 }, gender: { page: 0, x: 416.16, y: 570.24, fontSize: 11.0 } },
  'widow_pension_karnataka.pdf': { name: { page: 0, x: 404.82, y: 707.52, fontSize: 11.0 }, age: { page: 0, x: 404.82, y: 694.86, fontSize: 11.0 }, address: { page: 0, x: 404.82, y: 682.14, fontSize: 11.0 }, gender: { page: 0, x: 404.82, y: 606.18, fontSize: 11.0 } },
};

const schemeTemplateMap = {
  'ka-widow-pension': 'pension1.pdf',
  'ka-old-age-pension': 'pension1.pdf',
  'ka-disability-pension': 'disabledgovt.pdf',
  'pmjay': 'Application_for_assiatance.pdf',
  'pm-kisan': 'jobskilltraining.pdf'
};

const data = firstNodeJson('Build Response Data') || firstNodeJson('Store in Supabase') || ($input.first().json || {});
const parseData = firstNodeJson('Parse Profile + Hash') || {};

let profile = data.user_profile;
if (typeof profile === 'string') {
  try { profile = JSON.parse(profile); } catch (e) { profile = {}; }
}
if (!profile) profile = {};

const schemes = data.eligible_schemes || [];
const schemeIdRaw = data.scheme_id || (schemes[0] && schemes[0].scheme_id) || 'unknown';
const schemeId = String(schemeIdRaw).replace(/[^A-Za-z0-9_-]/g, '_');
const callIdRaw = parseData.call_id || data.call_id || ('call_' + Date.now());
const callId = String(callIdRaw).replace(/[^A-Za-z0-9_-]/g, '_');
const householdHashRaw = data.household_id_hash || parseData.household_id_hash || '';
const householdHash = String(householdHashRaw || '').replace(/[^a-fA-F0-9]/g, '').toLowerCase();
const storagePrefix = householdHash || callId;
const templateKey = data.pdf_template_key || (schemes[0] && schemes[0].pdf_template_key) || schemeTemplateMap[schemeIdRaw] || schemeTemplateMap[schemeId] || null;
if (!templateKey) {
  throw new Error('Missing pdf_template_key for scheme: ' + schemeId);
}

const blockedTemplateKeys = new Set(['widow_pension_karnataka.pdf','old_age_pension_karnataka.pdf','pmjay_enrollment.pdf']);
if (blockedTemplateKeys.has(templateKey)) {
  throw new Error('Blocked legacy placeholder template key: ' + templateKey);
}

const overlayMap = fieldMap[templateKey];
if (!overlayMap) {
  throw new Error('Missing coordinate mapping for template: ' + templateKey);
}

const requiredOverlayFields = ['name', 'age', 'address', 'gender'];
for (const f of requiredOverlayFields) {
  if (!overlayMap[f]) {
    throw new Error('Missing coordinate mapping for field "' + f + '" in template: ' + templateKey);
  }
}
const profileVals = {
  name: sanitize(profile.name || profile.applicant_name || 'Applicant'),
  age: sanitize(String(profile.age || '')),
  address: sanitize(profile.address || [profile.district, profile.state_code].filter(Boolean).join(', ') || 'Not Provided'),
  gender: sanitize(profile.gender || 'Not Provided')
};
const missingProfileFields = Object.entries(profileVals)
  .filter(([, v]) => !v || v === 'Not Provided')
  .map(([k]) => k);

const inputBinary = ($input.first() && $input.first().binary) || {};
const binaryKey = inputBinary.data ? 'data' : Object.keys(inputBinary)[0];
if (!binaryKey || !inputBinary[binaryKey] || !inputBinary[binaryKey].data) {
  throw new Error('Template binary missing from Fetch Template node');
}

let rawTemplateBytes;
try {
  rawTemplateBytes = await this.helpers.getBinaryDataBuffer(0, binaryKey);
} catch (e) {
  const raw = inputBinary[binaryKey].data;
  rawTemplateBytes = Buffer.isBuffer(raw) ? raw : Buffer.from(raw, 'base64');
}

const pdfHeaderIndex = rawTemplateBytes.indexOf('%PDF-');
if (pdfHeaderIndex < 0) {
  throw new Error('Template is not a valid PDF for key: ' + templateKey);
}
const templateBytes = rawTemplateBytes.slice(pdfHeaderIndex);
if (templateBytes.length < 5000) {
  throw new Error('Blocked placeholder-like template (too small) for key: ' + templateKey);
}
const pdfDoc = await PDFDocument.load(templateBytes);
const pages = pdfDoc.getPages();
if (!pages.length) {
  throw new Error('Template has no pages: ' + templateKey);
}

const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
for (const [field, pos] of Object.entries(overlayMap)) {
  const value = sanitize(profileVals[field] || '');
  if (!value) continue;
  const pageIdx = Math.max(0, Math.min(Number(pos.page || 0), pages.length - 1));
  pages[pageIdx].drawText(value, {
    x: Number(pos.x || 140),
    y: Number(pos.y || 650),
    size: Number(pos.fontSize || 11),
    font
  });
}

const pdfBytes = await pdfDoc.save();
const filename = callId + '_' + schemeId + '_application.pdf';
const objectKey = storagePrefix + '/filled_forms/' + schemeId + '.pdf';

return {
  json: {
    status: 'success',
    render_mode: 'template_overlay_only',
    call_id: callId,
    household_id_hash: data.household_id_hash || parseData.household_id_hash || null,
    scheme_id: schemeId,
    filename: filename,
    object_key: objectKey,
    file_size: pdfBytes.length,
    generated_at: new Date().toISOString(),
    template_used: templateKey,
    overlay_fields_applied: Object.keys(overlayMap),
    missing_profile_fields: missingProfileFields,
    user_profile: profileVals
  },
  binary: {
    data: {
      data: Buffer.from(pdfBytes).toString('base64'),
      mimeType: 'application/pdf',
      fileName: filename
    }
  }
};

