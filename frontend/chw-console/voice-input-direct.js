/**
 * ZELIA Voice Input Handler - Direct Ultravox Integration (No n8n)
 * This version calls Ultravox API directly from frontend
 */

import { UltravoxSession } from 'ultravox-client';

class VoiceInputHandler {
    constructor() {
        this.session = null;
        this.isRecording = false;
        this.callId = null;
    }

    /**
     * Start voice input session - DIRECT ULTRAVOX CALL
     */
    async startVoiceInput() {
        if (this.isRecording) {
            console.log('Already recording');
            return;
        }

        try {
            console.log('🎤 Starting voice session (direct Ultravox)...');
            this.updateUI('connecting');

            // Call Ultravox API directly (no n8n)
            const response = await fetch('https://api.ultravox.ai/v1/calls', {
                method: 'POST',
                headers: {
                    'X-API-Key': 'YOUR_ULTRAVOX_API_KEY',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    systemPrompt: `You are a government scheme assistant for India. Listen carefully to the user's voice query about government schemes.

Extract:
1. INTENT: eligibility, search, or apply
2. ENTITIES: age, marital_status, state, income_category
3. SCHEME TYPE: pension, housing, education, etc.

After user finishes speaking, respond ONLY with this JSON:
{
  "intent": "search",
  "entities": {"age": 65, "marital_status": "widow", "state": "Karnataka"},
  "scheme_type": "pension",
  "transcript": "full user transcript here"
}

Be concise and only return JSON.`,
                    maxDuration: 180
                })
            });

            if (!response.ok) {
                throw new Error(`Ultravox API error: ${response.status}`);
            }

            const data = await response.json();
            console.log('✅ Got Ultravox response:', data);

            const { joinUrl, callId } = data;
            this.callId = callId;

            // Create Ultravox session
            this.session = new UltravoxSession();

            // Set up event listeners
            this.setupEventListeners();

            // Join the call
            console.log('🔌 Connecting to Ultravox...');
            await this.session.joinCall(joinUrl);

            console.log('✅ Voice session active!');

        } catch (error) {
            console.error('❌ Error starting voice input:', error);
            this.updateUI('error');
            alert('Failed to start voice input: ' + error.message);
            this.cleanup();
        }
    }

    /**
     * Set up event listeners for Ultravox session
     */
    setupEventListeners() {
        this.session.addEventListener('status', (event) => {
            console.log('📊 Status:', event.state);

            if (event.state === 'active') {
                this.isRecording = true;
                this.updateUI('recording');
                this.showNotification('🎤 Listening... Speak now!', 'info');
            }

            if (event.state === 'disconnected' || event.state === 'ended') {
                this.stopVoiceInput();
            }
        });

        this.session.addEventListener('transcripts', (event) => {
            console.log('👤 User said:', event.text);
            this.displayTranscript(event.text, 'user');
        });

        this.session.addEventListener('message', (event) => {
            console.log('🤖 AI response:', event.text);
            this.displayTranscript(event.text, 'ai');

            try {
                const extracted = JSON.parse(event.text);
                if (extracted.intent) {
                    console.log('✨ Extracted data:', extracted);
                    this.handleExtractedData(extracted);
                }
            } catch (e) {
                console.log('Not JSON, continuing...');
            }
        });

        this.session.addEventListener('error', (event) => {
            console.error('❌ Session error:', event);
            this.showNotification('Error: ' + event.message, 'error');
        });
    }

    async stopVoiceInput() {
        console.log('🛑 Stopping voice session...');

        if (this.session) {
            try {
                await this.session.leaveCall();
            } catch (e) {
                console.error('Error leaving call:', e);
            }
        }

        this.cleanup();
        this.updateUI('stopped');
        this.showNotification('Voice input stopped', 'info');
    }

    cleanup() {
        this.session = null;
        this.isRecording = false;
        this.callId = null;
    }

    handleExtractedData(data) {
        console.log('🎯 Processing extracted data...');
        this.displayExtractedInfo(data);

        // Mock search for now (replace with actual RAG search)
        this.mockSearchSchemes(data);

        setTimeout(() => this.stopVoiceInput(), 1000);
    }

    mockSearchSchemes(voiceData) {
        // Mock results for testing
        const mockResults = {
            success: true,
            query: voiceData.transcript,
            schemes: [
                {
                    name: "National Widow Pension Scheme",
                    description: "Financial assistance for widows aged 40-79 years from BPL families",
                    score: 0.95,
                    category: "Social Welfare"
                },
                {
                    name: "Indira Gandhi National Widow Pension",
                    description: "Central government pension scheme for widows",
                    score: 0.88,
                    category: "Pension"
                }
            ]
        };

        console.log('🔍 Mock search results:', mockResults);
        this.displayResults(mockResults);
        this.showNotification('Found schemes!', 'success');
    }

    updateUI(state) {
        const button = document.getElementById('voice-button');
        const indicator = document.getElementById('recording-indicator');

        if (!button) return;

        switch (state) {
            case 'connecting':
                button.textContent = '⏳ Connecting...';
                button.disabled = true;
                break;

            case 'recording':
                button.textContent = '🛑 Stop Recording';
                button.classList.add('recording');
                button.disabled = false;
                if (indicator) indicator.style.display = 'block';
                break;

            case 'stopped':
                button.textContent = '🎤 Start Voice Input';
                button.classList.remove('recording');
                button.disabled = false;
                if (indicator) indicator.style.display = 'none';
                break;

            case 'error':
                button.textContent = '⚠️ Error - Try Again';
                button.classList.remove('recording');
                button.disabled = false;
                if (indicator) indicator.style.display = 'none';
                break;
        }
    }

    displayTranscript(text, speaker) {
        const display = document.getElementById('transcript-display');
        if (!display) return;

        const line = document.createElement('div');
        line.className = `transcript-line transcript-${speaker}`;
        line.innerHTML = `<strong>${speaker === 'user' ? '👤 You' : '🤖 AI'}:</strong> ${text}`;
        display.appendChild(line);
        display.scrollTop = display.scrollHeight;
    }

    displayExtractedInfo(data) {
        const container = document.getElementById('extracted-info');
        if (!container) return;

        container.innerHTML = `
      <h3>📊 Extracted Information</h3>
      <div class="info-grid">
        <div class="info-item">
          <span class="label">Intent:</span>
          <span class="value">${data.intent}</span>
        </div>
        ${data.scheme_type ? `
          <div class="info-item">
            <span class="label">Scheme Type:</span>
            <span class="value">${data.scheme_type}</span>
          </div>
        ` : ''}
        ${Object.entries(data.entities || {}).map(([key, value]) => `
          <div class="info-item">
            <span class="label">${key}:</span>
            <span class="value">${value}</span>
          </div>
        `).join('')}
      </div>
    `;
        container.style.display = 'block';
    }

    displayResults(results) {
        const container = document.getElementById('search-results');
        if (!container) return;

        if (!results.schemes || results.schemes.length === 0) {
            container.innerHTML = '<p class="no-results">No schemes found.</p>';
            return;
        }

        container.innerHTML = '<h3>🎯 Found Schemes:</h3>';

        results.schemes.forEach(scheme => {
            const card = document.createElement('div');
            card.className = 'scheme-card';
            card.innerHTML = `
        <h4>${scheme.name}</h4>
        <p>${scheme.description || scheme.content?.substring(0, 200)}</p>
        <div class="scheme-meta">
          <span class="score">Match: ${(scheme.score * 100).toFixed(0)}%</span>
          ${scheme.category ? `<span class="category">${scheme.category}</span>` : ''}
        </div>
      `;
            container.appendChild(card);
        });
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
}

// Initialize
const voiceHandler = new VoiceInputHandler();

// Attach to button
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initVoice);
} else {
    initVoice();
}

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
}

export default voiceHandler;
