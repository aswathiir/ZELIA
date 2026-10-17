let currentInterviewId = null;
let currentQuestionId = null;
let currentQuestionType = null;
let recognition = null;
let synth = window.speechSynthesis;

// === Voice Setup ===
// === Voice Setup & Fallback ===
let voiceAvailable = false;
let listeningTimeout = null;
// `recognition` is already declared above, so no need to redeclare here.

if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';

    recognition.onstart = function () {
        updateStatus("Listening...", "active");
        document.querySelector('.btn-mic').classList.add('pulse');

        // Safety Timeout: If no speech heard in 5s, switch to sim
        clearTimeout(listeningTimeout);
        listeningTimeout = setTimeout(() => {
            console.warn("Voice timeout - switching to sim");
            try { recognition.stop(); } catch (e) { }
            runSimulationSequence();
        }, 5000);
    };

    recognition.onresult = function (event) {
        clearTimeout(listeningTimeout);
        document.querySelector('.btn-mic').classList.remove('pulse');
        let transcript = event.results[0][0].transcript;
        document.getElementById('answer-input').value = transcript;
        updateStatus("Heard: " + transcript);
    };

    recognition.onerror = function (event) {
        clearTimeout(listeningTimeout);
        document.querySelector('.btn-mic').classList.remove('pulse');
        console.warn("Voice Error:", event.error);
        if (event.error === 'no-speech') {
            // Just stop pulsing, don't necessarily sim unless user clicks again? 
            // Or sim for smoothness
            runSimulationSequence();
        } else {
            runSimulationSequence();
        }
    };

    // Check if online
    if (navigator.onLine) {
        voiceAvailable = true;
    }
}

// === TTS Logic ===
let selectedVoice = null;
function loadVoices() {
    const voices = synth.getVoices();
    // Try to find a specific "Robotic" or Standard US voice
    // "Google US English" or "Microsoft Zira" often sound standard/robotic
    selectedVoice = voices.find(v => v.name.includes('Google US English')) ||
        voices.find(v => v.name.includes('Zira')) ||
        voices.find(v => v.lang === 'en-US');
}

if (speechSynthesis.onvoiceschanged !== undefined) {
    speechSynthesis.onvoiceschanged = loadVoices;
}

function updateStatus(msg, type = "normal") {
    const el = document.getElementById('status-msg');
    el.innerText = msg;
    if (type === "error") el.style.color = "red";
    else if (type === "active") el.style.color = "blue";
    else el.style.color = "#666";
}

function speak(text) {
    if (synth.speaking) synth.cancel();
    if (text !== '') {
        const utterThis = new SpeechSynthesisUtterance(text);
        if (!selectedVoice) loadVoices();
        if (selectedVoice) utterThis.voice = selectedVoice;

        // Robotic settings
        utterThis.pitch = 1.0; // Flat
        utterThis.rate = 1.0;  // Steady

        synth.speak(utterThis);
    }
}

// === Core Logic ===

async function startInterview() {
    document.getElementById('start-screen').style.display = 'none';
    document.getElementById('interview-screen').style.display = 'flex';

    const res = await fetch('/api/start_interview', { method: 'POST' });
    const data = await res.json();

    if (data.status === 'success') {
        currentInterviewId = data.interview_id;
        renderQuestion(data.question);
    }
}

function renderQuestion(q) {
    currentQuestionId = q.id;
    currentQuestionType = q.type;

    document.getElementById('question-text').innerText = q.text;
    document.getElementById('pictogram').innerText = q.pictogram_icon || "❓";
    document.getElementById('answer-input').value = "";
    updateStatus("Waiting for answer...");

    // Document Upload UI
    if (q.normalized_key === 'documents_held') {
        document.getElementById('doc-upload-container').style.display = 'block';
    } else {
        document.getElementById('doc-upload-container').style.display = 'none';
    }

    // TTS
    speak(q.text);
}

function toggleMic() {
    if (recognition) {
        try {
            recognition.start();
        } catch (e) {
            console.log("Already started or error");
        }
    } else {
        alert("Voice not supported");
    }
}

async function submitAnswer() {
    const answer = document.getElementById('answer-input').value;
    if (!answer && currentQuestionType !== 'multi_select') {
        updateStatus("Please provide an answer", "error");
        return;
    }

    const res = await fetch('/api/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            interview_id: currentInterviewId,
            question_id: currentQuestionId,
            answer: answer
        })
    });

    const data = await res.json();

    if (data.status === 'continue') {
        renderQuestion(data.question);
    } else if (data.status === 'completed') {
        showResults();
    }
}

// === Demo / Simulation ===
const demoAnswers = {
    "q_name": "Rithu",
    "q_age": "62",
    "q_gender": "Female",
    "q_marital": "Widowed",
    "q_children_count": "0",
    "q_occupation": "Unemployed",
    "q_income": "3000",
    "q_housing": "Kutcha",
    "q_disability": "No",
    "q_docs": "Ration Card, Aadhar"
};

function simulateDemo() {
    const ans = demoAnswers[currentQuestionId] || "Test Answer";
    document.getElementById('answer-input').value = ans;
    speak(ans); // Audit feedback
}

// === File Upload ===
async function handleFileUpload(input) {
    if (input.files && input.files[0]) {
        const formData = new FormData();
        formData.append('file', input.files[0]);

        document.getElementById('upload-status').innerText = "Scanning...";

        const res = await fetch('/api/upload_document', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.status === 'success') {
            document.getElementById('upload-status').innerText = "✅ Found: " + data.extracted_data.doc_type;
            // Auto-add to input
            let currentVal = document.getElementById('answer-input').value;
            if (currentVal) currentVal += ", ";
            currentVal += "Ration Card";
            document.getElementById('answer-input').value = currentVal;
        }
    }
}

// === Results ===
async function showResults() {
    document.getElementById('interview-screen').style.display = 'none';
    document.getElementById('results-screen').style.display = 'block';
    document.getElementById('results-list').innerText = "Calculating eligibility...";

    const res = await fetch(`/api/results/${currentInterviewId}`);
    const data = await res.json();

    const container = document.getElementById('results-list');
    container.innerHTML = "";

    data.results.forEach(r => {
        const div = document.createElement('div');
        div.className = `result-card ${r.eligible ? 'eligible' : 'ineligible'}`;

        const badgeClass = r.eligible ? 'success' : 'error';
        const badgeText = r.eligible ? 'ELIGIBLE' : 'NOT ELIGIBLE';

        div.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center">
                <h3>${r.scheme_id.replace('scheme_', '').replace(/_/g, ' ').toUpperCase()}</h3>
                <span class="badge ${badgeClass}">${badgeText}</span>
            </div>
            <p>${r.eligible ? "You can apply for this scheme." : "Criteria not met."}</p>
            ${!r.eligible ? `<small style='color:red'>Reasons: ${r.reasons.join(", ")}</small>` : ""}
        `;
        container.appendChild(div);
    });
}
