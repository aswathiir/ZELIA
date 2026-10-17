Provide real recordings and references for ASR QA.

Manifest format (`manifest.jsonl`):

```json
{"audio_path":"samples/en_01.wav","language":"en-IN","reference":"My name is Lakshmi and I am 65 years old"}
{"audio_path":"samples/ta_01.wav","language":"ta-IN","reference":"என் பெயர் லக்ஷ்மி எனக்கு 65 வயது"}
```

Notes:
- `audio_path` can be relative to this folder or absolute.
- Use clean ground-truth references.
- Generate missing samples using local voice service TTS:
  - `python3 scripts/generate_audio_qa_samples.py --manifest data/audio_qa/manifest.jsonl --voice-endpoint http://localhost:8018 --prefer-local-say`
- Run:
  - `python3 scripts/asr_multilingual_qa.py --manifest data/audio_qa/manifest.jsonl --voice-endpoint http://localhost:8018`
