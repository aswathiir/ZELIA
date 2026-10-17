import { UltravoxSession } from 'https://esm.run/ultravox-client';

const API_BASE = 'http://localhost:5678/webhook';
let currentSession = null;
let fullTranscript = '';

document.getElementById('startVoice').addEventListener('click', startVoiceCall);
document.getElementById('endVoice').addEventListener('click', endVoiceCall);

async function startVoiceCall() {
    try {
        updateStatus('Creating voice session...');
        
        const response = await fetch('http://localhost:8006/create-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                language: 'ta-IN',
                context: { mode: 'scheme_discovery' }
            })
        });
        
        const { join_url } = await response.json();
        
        currentSession = new UltravoxSession();
        await currentSession.joinCall(join_url);
        
        currentSession.addEventListener('status', handleStatusChange);
        currentSession.addEventListener('transcripts', handleTranscript);
        
        document.getElementById('startVoice').disabled = true;
        document.getElementById('endVoice').disabled = false;
        updateStatus('Call connected - You can speak now');
        
    } catch (error) {
        updateStatus('Error: ' + error.message, 'error');
    }
}

async function endVoiceCall() {
    if (currentSession) {
        await currentSession.leaveCall();
        currentSession = null;
        
        document.getElementById('startVoice').disabled = false;
        document.getElementById('endVoice').disabled = true;
        updateStatus('Call ended');
        
        // Process transcript
        if (fullTranscript) {
            await processTranscript(fullTranscript);
        }
    }
}

function handleStatusChange(event) {
    updateStatus(`Status: ${event.state}`);
}

function handleTranscript(event) {
    const transcriptDiv = document.getElementById('transcript');
    fullTranscript += event.text + '\n';
    transcriptDiv.textContent = fullTranscript;
}

async function processTranscript(transcript) {
    try {
        updateStatus('Processing transcript...');
        
        const response = await fetch(`${API_BASE}/zelia-voice-assist`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transcript: transcript,
                user_id: 'chw_001',
                language: 'ta-IN',
                state_code: 'TN'
            })
        });
        
        const result = await response.json();
        displaySchemes(result.schemes);
        displayActions(result.action_items);
        updateStatus('Processing complete!', 'success');
        
    } catch (error) {
        updateStatus('Processing error: ' + error.message, 'error');
    }
}

function displaySchemes(schemes) {
    const schemesDiv = document.getElementById('schemes');
    schemesDiv.innerHTML = schemes.map(scheme => `
        <div class="scheme-card">
            <h3>${scheme.scheme_id}</h3>
            <p>Confidence: ${(scheme.confidence * 100).toFixed(0)}%</p>
            <p>Missing docs: ${scheme.missing_docs.join(', ')}</p>
        </div>
    `).join('');
}

function displayActions(actions) {
    const actionsDiv = document.getElementById('actions');
    actionsDiv.innerHTML = actions.map((action, i) => `
        <div class="action-card">
            <h4>Step ${i + 1}: ${action.scheme_id}</h4>
            <ul>
                ${action.next_steps.map(step => `<li>${step}</li>`).join('')}
            </ul>
        </div>
    `).join('');
}

function updateStatus(message, type = 'info') {
    const statusDiv = document.getElementById('voiceStatus');
    statusDiv.textContent = message;
    statusDiv.className = `status-box ${type}`;
}