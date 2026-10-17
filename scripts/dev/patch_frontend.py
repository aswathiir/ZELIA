import re
with open("frontend/zelia-core-desktop/frontend/src/pages/CallInProgress.jsx", "r") as f:
    data = f.read()

# Fix the sendText function so it appends the message to transcript natively
new_send_text = """    const sendText = () => {
        if (!textMsg.trim() || !sessionRef.current) return;
        try {
            const msg = textMsg.trim();
            sessionRef.current.sendText(msg);
            
            // Explicitly add it to our frontend transcript state so it doesn't get lost
            // if the Ultravox SDK doesn't echo it back immediately.
            setTranscript(prev => [...prev, {
                id: prev.length,
                from: 'user',
                text: msg,
                isFinal: true,
                time: new Date().toTimeString().slice(0, 5),
            }]);
            
            setTextMsg('');
        } catch (e) {
            console.error('Send text error:', e);
        }
    };"""

data = re.sub(
    r"    const sendText = \(\) => {\n        if \(\!textMsg\.trim\(\).*?\n        \} catch \(e\) {\n            console\.error\('Send text error:', e\);\n        }\n    };",
    new_send_text,
    data,
    flags=re.DOTALL
)

with open("frontend/zelia-core-desktop/frontend/src/pages/CallInProgress.jsx", "w") as f:
    f.write(data)
print("Patched.")
