"""
ZELIA - Multilingual Support with Sarvam AI
Adds Hindi, Tamil, Telugu and other Indian language support
"""
import os
import requests
from typing import Dict, List
import json

class SarvamTranslator:
    """Sarvam AI Translation Service"""
    
    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        self.base_url = "https://api.sarvam.ai"
        self.supported_languages = {
            "hi": "Hindi",
            "ta": "Tamil",
            "te": "Telugu",
            "bn": "Bengali",
            "mr": "Marathi",
            "gu": "Gujarati",
            "kn": "Kannada",
            "ml": "Malayalam",
            "pa": "Punjabi",
            "or": "Odia"
        }
    
    def translate(self, text: str, source_lang: str = "en", target_lang: str = "hi") -> str:
        """
        Translate text using Sarvam AI (REAL API ONLY - NO FALLBACK)
        
        Args:
            text: Text to translate
            source_lang: Source language code (default: en)
            target_lang: Target language code (default: hi for Hindi)
        
        Returns:
            Translated text
        """
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY is required! Set it in .env file or environment variable.")
        
        try:
            response = requests.post(
                f"{self.base_url}/translate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "input": text,
                    "source_language_code": source_lang,
                    "target_language_code": target_lang,
                    "speaker_gender": "Male",
                    "mode": "formal",
                    "model": "mayura:v1",
                    "enable_preprocessing": True
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("translated_text", text)
            else:
                error_msg = f"Sarvam AI API error {response.status_code}: {response.text}"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)
                
        except requests.exceptions.Timeout:
            raise Exception("Sarvam AI API timeout - request took too long")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Sarvam AI API - check internet connection")
        except Exception as e:
            raise Exception(f"Translation failed: {str(e)}")

    
    def _mock_translate(self, text: str, target_lang: str) -> str:
        """Mock translation for testing without API key"""
        # Simple keyword translations for common scheme terms
        translations = {
            "hi": {  # Hindi
                "pension": "पेंशन",
                "widow": "विधवा",
                "old age": "वृद्धावस्था",
                "disability": "विकलांगता",
                "housing": "आवास",
                "scheme": "योजना",
                "eligibility": "पात्रता",
                "benefits": "लाभ",
                "documents": "दस्तावेज़",
                "apply": "आवेदन करें"
            },
            "ta": {  # Tamil
                "pension": "ஓய்வூதியம்",
                "widow": "விதவை",
                "old age": "முதுமை",
                "disability": "ஊனம்",
                "housing": "வீட்டுவசதி",
                "scheme": "திட்டம்",
                "eligibility": "தகுதி",
                "benefits": "நன்மைகள்",
                "documents": "ஆவணங்கள்",
                "apply": "விண்ணப்பிக்கவும்"
            },
            "te": {  # Telugu
                "pension": "పెన్షన్",
                "widow": "వితంతువు",
                "old age": "వృద్ధాప్యం",
                "disability": "వైకల్యం",
                "housing": "గృహనిర్మాణం",
                "scheme": "పథకం",
                "eligibility": "అర్హత",
                "benefits": "ప్రయోజనాలు",
                "documents": "పత్రాలు",
                "apply": "దరఖాస్తు చేయండి"
            }
        }
        
        if target_lang in translations:
            text_lower = text.lower()
            for eng, translated in translations[target_lang].items():
                if eng in text_lower:
                    text = text.replace(eng, translated)
                    text = text.replace(eng.title(), translated)
        
        return text
    
    def detect_language(self, text: str) -> str:
        """Detect language of input text"""
        # Simple detection based on Unicode ranges
        if any('\u0900' <= c <= '\u097F' for c in text):  # Devanagari (Hindi)
            return "hi"
        elif any('\u0B80' <= c <= '\u0BFF' for c in text):  # Tamil
            return "ta"
        elif any('\u0C00' <= c <= '\u0C7F' for c in text):  # Telugu
            return "te"
        else:
            return "en"

def translate_scheme_data(schemes_file: str, target_lang: str = "hi"):
    """Translate scheme data to target language"""
    translator = SarvamTranslator()
    
    print(f"Translating schemes to {translator.supported_languages.get(target_lang, target_lang)}...")
    
    try:
        with open(schemes_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        schemes = data.get("schemes", [])
        translated_schemes = []
        
        for scheme in schemes:
            print(f"  Translating: {scheme['name'][:50]}...")
            
            translated_scheme = scheme.copy()
            translated_scheme['name_translated'] = translator.translate(scheme['name'], target_lang=target_lang)
            translated_scheme['description_translated'] = translator.translate(scheme['description'], target_lang=target_lang)
            
            translated_schemes.append(translated_scheme)
        
        # Save translated data
        output_file = schemes_file.replace('.json', f'_{target_lang}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "schemes": translated_schemes,
                "total": len(translated_schemes),
                "language": target_lang
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved translated schemes to: {output_file}")
        return output_file
        
    except Exception as e:
        print(f"✗ Error translating schemes: {e}")
        return None

if __name__ == "__main__":
    print("=" * 70)
    print("ZELIA Multilingual Support - Sarvam AI Integration")
    print("=" * 70)
    print()
    
    # Initialize translator
    translator = SarvamTranslator()
    
    print("Supported Languages:")
    for code, name in translator.supported_languages.items():
        print(f"  {code}: {name}")
    print()
    
    # Test translation
    test_text = "widow pension scheme eligibility"
    print(f"Test Translation:")
    print(f"  English: {test_text}")
    print(f"  Hindi: {translator.translate(test_text, target_lang='hi')}")
    print(f"  Tamil: {translator.translate(test_text, target_lang='ta')}")
    print(f"  Telugu: {translator.translate(test_text, target_lang='te')}")
    print()
    
    # Translate scheme data
    schemes_file = "schemes_data/myscheme_dataset.json"
    if os.path.exists(schemes_file):
        print("Translating scheme database...")
        translate_scheme_data(schemes_file, target_lang="hi")
    else:
        print(f"⚠ Schemes file not found: {schemes_file}")
    
    print("\n" + "=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print("\nTo use Sarvam AI:")
    print("  1. Get API key from: https://www.sarvam.ai/")
    print("  2. Set environment variable: SARVAM_API_KEY=your_key")
    print("  3. Run this script again for real translations")
