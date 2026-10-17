# Translation Service - Sarvam AI

Multilingual translation microservice for ZELIA using Sarvam AI.

## Supported Languages
- English (en-IN)
- Hindi (hi-IN)
- Tamil (ta-IN)
- Malayalam (ml-IN)
- Telugu (te-IN)
- Bengali (bn-IN)
- Marathi (mr-IN)
- Gujarati (gu-IN)
- Kannada (kn-IN)
- Punjabi (pa-IN)
- Odia (or-IN)

## Endpoints

### POST /translate
Single text translation
```json
{
  "text": "pension scheme",
  "source_lang": "en-IN",
  "target_lang": "hi-IN"
}
```

### POST /translate/batch
Batch translation for multiple texts
```json
{
  "texts": ["pension", "widow", "eligibility"],
  "source_lang": "en-IN",
  "target_lang": "ta-IN"
}
```

### POST /translate/document
Translate document fields with canonical mapping
```json
{
  "fields": {
    "head_name": "John Doe",
    "age": "65",
    "marital_status": "widow"
  },
  "target_lang": "hi-IN"
}
```

## Environment Variables
```
SARVAM_API_KEY=your_api_key_here
REDIS_URL=redis://localhost:6379/0
PORT=8009
```

## Docker
```bash
docker build -t translation-service .
docker run -p 8009:8009 --env-file .env translation-service
```
