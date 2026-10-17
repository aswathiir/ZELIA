/**
 * ZELIA Voice Input Handler - Full Integration with n8n Workflow
 * Connects to local Ultravox proxy and triggers n8n workflow
 */

class VoiceInputHandler {
    constructor() {
        this.isRecording = false;
        this.callId = null;
        this.mediaRecorder = null;
        this.audioChunks = [];

        // Configuration
        this.config = {
            ultravoxProxyUrl: 'http://localhost:8010',
            n8nWebhookUrl: 'http://localhost:5678/webhook/ultravox/call-ended',
            voiceProcessorUrl: 'http://localhost:8018',
            language: 'en-IN',
            localVoiceEnabled: true,
            requireLiveUltravox: true
        };
    }

    /**
     * Start voice input session via Ultravox Proxy
     */
    async startVoiceInput() {
        if (this.isRecording) {
            console.log('Already recording');
            return;
        }

        try {
            console.log('🎤 Starting voice session...');
            this.updateUI('connecting');

            // Step 1: Create session via local Ultravox proxy
            const sessionResponse = await fetch(`${this.config.ultravoxProxyUrl}/create-session`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    language: this.config.language,
                    context: {
                        user: 'chw_user',
                        purpose: 'scheme_query'
                    }
                })
            });

            if (!sessionResponse.ok) {
                const errorText = await sessionResponse.text();
                console.error('Session creation failed:', sessionResponse.status, errorText);
                throw new Error(`Failed to create session: ${sessionResponse.status} - ${errorText}`);
            }

            const sessionData = await sessionResponse.json();
            console.log('✅ Session created:', sessionData);

            this.callId = sessionData.call_id;

            // Check if we got a join URL (for WebRTC connection)
            if (sessionData.join_url) {
                // Real Ultravox WebRTC session
                await this.connectToUltravox(sessionData.join_url);
            } else {
                if (this.config.requireLiveUltravox) {
                    throw new Error('Live Ultravox join_url missing. Session is not valid for production flow.');
                }
                await this.startBrowserRecognition();
            }

        } catch (error) {
            console.error('❌ Error starting voice input:', error);
            this.updateUI('error');
            this.showNotification('Failed to start voice: ' + error.message, 'error');
            this.cleanup();
        }
    }

    /**
     * Connect to Ultravox via WebRTC (if available)
     */
    async connectToUltravox(joinUrl) {
        try {
            // Dynamic import of Ultravox client
            const { UltravoxSession } = await import('ultravox-client');

            this.session = new UltravoxSession();
            this.setupUltravoxListeners();
            await this.session.joinCall(joinUrl);

            this.isRecording = true;
            this.updateUI('recording');
            this.showNotification('🎤 Listening... Speak now!', 'info');

        } catch (error) {
            if (this.config.requireLiveUltravox) {
                throw error;
            }
            console.log('Ultravox WebRTC not available, using browser speech recognition');
            await this.startBrowserRecognition();
        }
    }

    /**
     * Fallback: Use browser's built-in speech recognition
     */
    async startBrowserRecognition() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            throw new Error('Speech recognition not supported in this browser');
        }

        this.recognition = new SpeechRecognition();
        this.recognition.lang = this.config.language;
        this.recognition.continuous = true;
        this.recognition.interimResults = true;

        this.transcriptBuffer = [];

        this.recognition.onstart = () => {
            console.log('🎤 Browser speech recognition started');
            this.isRecording = true;
            this.updateUI('recording');
            this.showNotification('🎤 Listening... Speak your query', 'info');
        };

        this.recognition.onresult = (event) => {
            let transcript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    this.transcriptBuffer.push(transcript.trim());
                    this.displayTranscript(transcript, 'user');
                }
            }
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error !== 'no-speech') {
                this.showNotification('Recognition error: ' + event.error, 'error');
            }
        };

        this.recognition.onend = () => {
            console.log('Speech recognition ended');
            this.finishSession();
        };

        this.recognition.start();
    }

    /**
     * Stop voice input and process transcript
     */
    async stopVoiceInput() {
        console.log('🛑 Stopping voice session...');

        // 1. Browser Speech Recognition Mode
        if (this.recognition) {
            // Just signal stop. The 'onend' handler will do the processing & cleanup.
            // This ensures we catch the final 'onresult' which fires AFTER stop().
            this.recognition.stop();
            this.updateUI('processing');
            return;
        }

        // 2. Ultravox WebRTC Mode (Synchronous cleanup)
        if (this.session) {
            try {
                await this.session.leaveCall();
            } catch (e) {
                console.error('Error leaving call:', e);
            }
        }

        this.finishSession();
    }

    /**
     * Shared logic to finalize session and process transcript
     */
    async finishSession() {
        this.isRecording = false;
        this.updateUI('processing');

        // If we have a transcript, process it
        if (this.transcriptBuffer && this.transcriptBuffer.length > 0) {
            await this.processTranscript();
        } else {
            console.warn("⚠️ No transcript to process");
        }

        this.cleanup();
        this.updateUI('stopped');
    }

    /**
     * Process the transcript through n8n workflow
     */
    async processTranscript() {
        let fullTranscript = this.transcriptBuffer.join(' ');
        console.log('📝 Full transcript:', fullTranscript);

        this.showNotification('Processing your query...', 'info');

        try {
            if (this.config.localVoiceEnabled && fullTranscript) {
                try {
                    const pre = await fetch(`${this.config.voiceProcessorUrl}/voice/process`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            call_id: this.callId || `browser_${Date.now()}`,
                            language: this.config.language,
                            transcript_text: fullTranscript
                        })
                    });
                    if (pre.ok) {
                        const preJson = await pre.json();
                        if (preJson.transcript) {
                            fullTranscript = preJson.transcript;
                        }
                    }
                } catch (e) {
                    console.warn('Voice processor unavailable, continuing with browser transcript');
                }
            }

            // Send to n8n workflow
            const response = await fetch(this.config.n8nWebhookUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    call_id: this.callId || `browser_${Date.now()}`,
                    customer_number: 'browser_session',
                    duration_secs: 0,
                    status: 'completed',
                    messages: [
                        { role: 'user', text: fullTranscript }
                    ],
                    metadata: {
                        citizen_id: 'citizen_browser',
                        scheme_id: null,
                        language: this.config.language
                    }
                })
            });

            if (!response.ok) {
                throw new Error(`Workflow error: ${response.status}`);
            }

            const result = await response.json();
            console.log('✅ Workflow response:', result);

            this.displayResults(result);
            this.speakResultSummary(result);
            this.showNotification('Query processed successfully!', 'success');

        } catch (error) {
            console.error('❌ Error processing transcript:', error);
            this.showNotification('Error: ' + error.message, 'error');

            // Fallback: Try direct API call
            await this.fallbackSchemeSearch(fullTranscript);
        }
    }

    /**
     * Fallback: Direct scheme search if n8n fails
     */
    async fallbackSchemeSearch(query) {
        try {
            console.log('Trying fallback search...');

            const response = await fetch('http://localhost:8007/search/keyword', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, k: 5 })
            });

            if (response.ok) {
                const data = await response.json();
                this.displayResults({ results: data.results || [] });
            }
        } catch (e) {
            console.error('Fallback search also failed:', e);
        }
    }

    setupUltravoxListeners() {
        this.session.addEventListener('status', (event) => {
            console.log('📊 Status:', event.state);
            if (event.state === 'active') {
                this.isRecording = true;
                this.updateUI('recording');
            }
        });

        this.session.addEventListener('transcripts', (event) => {
            this.displayTranscript(event.text, 'user');
            this.transcriptBuffer = this.transcriptBuffer || [];
            this.transcriptBuffer.push(event.text);
        });

        this.session.addEventListener('message', (event) => {
            this.displayTranscript(event.text, 'ai');
        });
    }

    cleanup() {
        this.session = null;
        this.recognition = null;
        this.callId = null;
        this.transcriptBuffer = [];
    }

    updateUI(state) {
        const button = document.getElementById('voice-button');
        const indicator = document.getElementById('recording-indicator');
        const statusText = document.getElementById('status-text');

        if (!button) return;

        const states = {
            connecting: { text: '⏳ Connecting...', disabled: true, class: '' },
            recording: { text: '🛑 Stop Recording', disabled: false, class: 'recording' },
            processing: { text: '⏳ Processing...', disabled: true, class: '' },
            stopped: { text: '🎤 Start Voice Input', disabled: false, class: '' },
            error: { text: '⚠️ Error - Try Again', disabled: false, class: '' }
        };

        const s = states[state] || states.stopped;
        button.textContent = s.text;
        button.disabled = s.disabled;
        button.className = s.class;

        if (indicator) {
            indicator.style.display = state === 'recording' ? 'block' : 'none';
        }

        if (statusText) {
            statusText.textContent = state.charAt(0).toUpperCase() + state.slice(1);
        }
    }

    displayTranscript(text, speaker) {
        const display = document.getElementById('transcript-display');
        if (!display) return;

        // Clear placeholder
        const placeholder = display.querySelector('.placeholder');
        if (placeholder) placeholder.remove();

        const line = document.createElement('div');
        line.className = `transcript-line transcript-${speaker}`;
        line.innerHTML = `<strong>${speaker === 'user' ? '👤 You' : '🤖 AI'}:</strong> ${text}`;
        display.appendChild(line);
        display.scrollTop = display.scrollHeight;
    }

    displayResults(data) {
        const container = document.getElementById('search-results');
        if (!container) return;

        container.innerHTML = '';

        const results = data.results || data.schemes || [];

        if (results.length === 0) {
            container.innerHTML = '<p class="no-results">No schemes found for your query.</p>';
            return;
        }

        container.innerHTML = '<h3>🎯 Found Schemes:</h3>';

        results.forEach(scheme => {
            const card = document.createElement('div');
            card.className = 'scheme-card';
            card.innerHTML = `
                <h4>${scheme.name || scheme.title}</h4>
                <p>${scheme.description || ''}</p>
                <div class="scheme-meta">
                    ${scheme.score ? `<span class="score">Match: ${(scheme.score * 100).toFixed(0)}%</span>` : ''}
                    ${scheme.category ? `<span class="category">${scheme.category}</span>` : ''}
                </div>
            `;
            container.appendChild(card);
        });
    }

    async speakResultSummary(data) {
        const results = data.results || data.schemes || data.eligible_schemes || [];
        const count = results.length;
        const summary = count > 0
            ? `Found ${count} eligible schemes. Top scheme is ${(results[0].name || results[0].title || results[0].scheme_name || 'available in the list')}.`
            : 'No eligible schemes found for the provided profile.';

        if (this.config.localVoiceEnabled) {
            try {
                const r = await fetch(`${this.config.voiceProcessorUrl}/tts/synthesize`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: summary, language: this.config.language })
                });
                if (r.ok) {
                    const tts = await r.json();
                    if (tts.audio_base64) {
                        const audio = new Audio(`data:${tts.mime_type || 'audio/wav'};base64,${tts.audio_base64}`);
                        await audio.play().catch(() => {});
                        return;
                    }
                }
            } catch (e) {
                console.warn('Local TTS unavailable, falling back to browser TTS');
            }
        }

        if ('speechSynthesis' in window) {
            const utter = new SpeechSynthesisUtterance(summary);
            utter.lang = this.config.language || 'en-IN';
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utter);
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        document.body.appendChild(notification);
        setTimeout(() => notification.classList.add('show'), 10);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    setLanguage(lang) {
        this.config.language = lang;
        console.log('Language set to:', lang);
    }
}

// Initialize
const voiceHandler = new VoiceInputHandler();

// Attach to button when DOM is ready
function initVoice() {
    const button = document.getElementById('voice-button');
    if (button) {
        button.addEventListener('click', () => {
            if (voiceHandler.isRecording) {
                voiceHandler.stopVoiceInput();
            } else {
                voiceHandler.startVoiceInput();
            }
        });
    }

    // Language selector
    const langSelect = document.getElementById('language-select');
    if (langSelect) {
        langSelect.addEventListener('change', (e) => {
            voiceHandler.setLanguage(e.target.value);
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoice);
} else {
    initVoice();
}

// Export for module usage
if (typeof module !== 'undefined') {
    module.exports = voiceHandler;
}
