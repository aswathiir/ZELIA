/**
 * speechHelper.js — v5
 *
 * Voice priority chain:
 *   1. Native Web Speech API voice (for languages with system/Chrome voices)
 *   2. ResponsiveVoice CDN (covers Tamil, Malayalam, and many other languages)
 *   3. English fallback text via en-IN Web Speech API
 *
 * ResponsiveVoice must be loaded in index.html:
 *   <script src="https://code.responsivevoice.org/responsivevoice.js?key=FREE"></script>
 */

/* ────────────────────────────────────────────
   ResponsiveVoice language map
──────────────────────────────────────────── */
const RV_VOICE_MAP = {
    'ta-IN': 'Tamil Female',
    'ml-IN': 'Malayalam Female',
    'hi-IN': 'Hindi Female',
    'te-IN': 'Telugu Female',
    'kn-IN': 'Kannada Female',
    'bn-IN': 'Bengali Female',
};

const isRVReady = () =>
    typeof window !== 'undefined' &&
    typeof window.responsiveVoice !== 'undefined' &&
    window.responsiveVoice.voiceSupport();

const speakViaRV = (text, langCode, onEnd) => {
    const voiceName = RV_VOICE_MAP[langCode];
    if (!voiceName || !isRVReady()) { onEnd?.(); return false; }
    window.responsiveVoice.speak(text, voiceName, {
        rate: 0.9,
        pitch: 1,
        onend: () => onEnd?.(),
        onerror: () => { console.warn('[RV] error for', voiceName); onEnd?.(); },
    });
    console.log(`[RV] Speaking "${voiceName}": "${text.slice(0, 50)}"`);
    return true;
};

const stopRV = () => {
    if (isRVReady()) window.responsiveVoice.cancel();
};

/* ────────────────────────────────────────────
   Module-level Web Speech voice cache
──────────────────────────────────────────── */
let _voices = [];
let _voicesLoaded = false;
const _waiting = [];

const _loadVoices = () => {
    const v = window.speechSynthesis.getVoices();
    if (v.length) {
        _voices = v;
        _voicesLoaded = true;
        _waiting.forEach(fn => fn());
        _waiting.length = 0;
    }
};

if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    window.speechSynthesis.addEventListener('voiceschanged', _loadVoices);
    _loadVoices();
}

const voicesReady = () =>
    new Promise(resolve => {
        if (_voicesLoaded) return resolve();
        _waiting.push(resolve);
        setTimeout(() => { _voices = window.speechSynthesis.getVoices(); _voicesLoaded = true; resolve(); }, 2000);
    });

/* ────────────────────────────────────────────
   Web Speech voice pickers
──────────────────────────────────────────── */
const pickVoice = (langCode) => {
    const prefix = langCode.split('-')[0];
    return (
        _voices.find(v => v.lang === langCode) ||
        _voices.find(v => v.lang.startsWith(prefix + '-')) ||
        _voices.find(v => v.lang === prefix) ||
        null
    );
};

const pickEnVoice = () =>
    _voices.find(v => v.lang === 'en-IN') ||
    _voices.find(v => v.lang.startsWith('en-')) ||
    _voices.find(v => v.lang.startsWith('en'));

/* ────────────────────────────────────────────
   Native Web Speech utterance
──────────────────────────────────────────── */
let _utt = null;
let _keepAlive = null;

const _clearKeepAlive = () => { if (_keepAlive) { clearInterval(_keepAlive); _keepAlive = null; } };

const _speakNative = (text, voice, langCode, onEnd) => {
    const utt = new SpeechSynthesisUtterance(text);
    if (voice) { utt.voice = voice; utt.lang = voice.lang; }
    else utt.lang = langCode;
    utt.rate = 0.85;
    utt.pitch = 1;
    const done = () => { _clearKeepAlive(); _utt = null; onEnd?.(); };
    utt.onend = done;
    utt.onerror = (e) => { if (e.error !== 'interrupted') console.warn('[Speech]', e.error); done(); };
    _utt = utt;
    window.speechSynthesis.speak(utt);
    _keepAlive = setInterval(() => {
        if (window.speechSynthesis.speaking) { window.speechSynthesis.pause(); window.speechSynthesis.resume(); }
        else _clearKeepAlive();
    }, 10000);
    console.log(`[Speech] Native: "${voice?.name ?? langCode}" → "${text.slice(0, 50)}"`);
};

/* ────────────────────────────────────────────
   Public API
──────────────────────────────────────────── */

/**
 * speak(text, langCode, onEnd?, fallbackText?)
 *
 * Priority order:
 *  1. Native Web Speech voice found for langCode → use it
 *  2. ResponsiveVoice CDN for regional languages (ta, ml, hi, etc.)
 *  3. English fallbackText via en-IN native voice
 */
export const speak = async (text, langCode, onEnd, fallbackText) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
        onEnd?.(); return;
    }

    stopSpeech();
    await new Promise(r => setTimeout(r, 150));
    await voicesReady();

    // ── English: always use native voice ──
    if (langCode.startsWith('en')) {
        _speakNative(text, pickEnVoice(), langCode, onEnd);
        return;
    }

    // ── Regional: try native voice first ──
    const nativeVoice = pickVoice(langCode);
    if (nativeVoice) {
        _speakNative(text, nativeVoice, langCode, onEnd);
        return;
    }

    // ── ResponsiveVoice fallback ──
    if (RV_VOICE_MAP[langCode] && isRVReady()) {
        speakViaRV(text, langCode, onEnd);
        return;
    }

    // ── If RV not ready yet, wait up to 3s then retry ──
    if (RV_VOICE_MAP[langCode]) {
        let waited = 0;
        const tryRV = setInterval(() => {
            waited += 200;
            if (isRVReady()) {
                clearInterval(tryRV);
                speakViaRV(text, langCode, onEnd);
            } else if (waited >= 3000) {
                clearInterval(tryRV);
                console.warn('[Speech] ResponsiveVoice not available. Using English fallback.');
                if (fallbackText) _speakNative(fallbackText, pickEnVoice(), 'en-IN', onEnd);
                else onEnd?.();
            }
        }, 200);
        return;
    }

    // ── Last resort: English fallback ──
    if (fallbackText) {
        console.warn(`[Speech] No voice for ${langCode} — English fallback`);
        _speakNative(fallbackText, pickEnVoice(), 'en-IN', onEnd);
    } else {
        onEnd?.();
    }
};

/** Stop all active speech (both native and ResponsiveVoice) */
export const stopSpeech = () => {
    _clearKeepAlive();
    stopRV();
    if (_utt) { _utt.onend = null; _utt.onerror = null; _utt = null; }
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
};

/** Returns available native voices for debug display */
export const listVoices = () =>
    _voices.map(v => `${v.name}  [${v.lang}]${v.localService ? '' : ' (online)'}`);
