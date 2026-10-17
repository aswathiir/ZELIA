from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import torch
from transformers import LayoutLMTokenizer, LayoutLMForTokenClassification
from PIL import Image
import io
import base64
import numpy as np

app = FastAPI(title="ZELIA Layout Analysis Service")

class OCRToken(BaseModel):
    text: str
    bbox: List[int]  # [x1, y1, x2, y2]

class LayoutRequest(BaseModel):
    tokens: List[OCRToken]
    image_base64: str
    width: int
    height: int

# Global model/tokenizer
tokenizer = None
model = None

@app.on_event("startup")
async def load_model():
    global tokenizer, model
    print("Loading LayoutLM fine-tuned on FUNSD dataset...")
    try:
        # Use pre-trained model fine-tuned on form understanding
        # FUNSD = Form Understanding in Noisy Scanned Documents
        tokenizer = LayoutLMTokenizer.from_pretrained("nielsr/layoutlm-finetuned-funsd")
        model = LayoutLMForTokenClassification.from_pretrained("nielsr/layoutlm-finetuned-funsd")
        print("✓ LayoutLM FUNSD model loaded successfully!")
        print("  This model is pre-trained for form field extraction (name, date, address, etc.)")
    except Exception as e:
        print(f"CRITICAL: Failed to load LayoutLM FUNSD model: {e}")
        print("Falling back to base model...")
        try:
            tokenizer = LayoutLMTokenizer.from_pretrained("microsoft/layoutlm-base-uncased")
            model = LayoutLMForTokenClassification.from_pretrained("microsoft/layoutlm-base-uncased")
            print("⚠ Base model loaded, but accuracy will be lower")
        except Exception as e2:
            print(f"CRITICAL: All models failed: {e2}")


@app.get("/health")
def health_check():
    status = "healthy" if model else "degraded"
    return {"status": status, "gpu_available": torch.cuda.is_available()}

@app.post("/extract")
async def extract_layout(request: LayoutRequest):
    if not model:
        raise HTTPException(503, "Model not loaded")

    try:
        # 1. Prepare Inputs for LayoutLM v1 (Text + BBox)
        # V1 doesn't use the visual image features in the base implementation easily without visual backbone
        # We will run text-only + spatial layout
        
        words = [t.text for t in request.tokens]
        boxes = []
        
        # Normalize boxes to 0-1000
        width, height = request.width, request.height
        for t in request.tokens:
            x1, y1, x2, y2 = t.bbox
            nx1 = int((x1 / width) * 1000)
            ny1 = int((y1 / height) * 1000)
            nx2 = int((x2 / width) * 1000)
            ny2 = int((y2 / height) * 1000)
            # Clamp 0-1000
            boxes.append([
                max(0, min(1000, nx1)), 
                max(0, min(1000, ny1)), 
                max(0, min(1000, nx2)), 
                max(0, min(1000, ny2))
            ])
            
        # 2. Tokenization
        # LayoutLM requires token-level boxes. We must split words and align boxes.
        token_boxes = []
        token_list = []
        
        for word, box in zip(words, boxes):
            word_tokens = tokenizer.tokenize(word)
            token_list.extend(word_tokens)
            token_boxes.extend([box] * len(word_tokens))
            
        # Truncate if needed (max 512 for BERT-like)
        if len(token_list) > 510:
            token_list = token_list[:510]
            token_boxes = token_boxes[:510]
            
        # Add special tokens
        token_list = [tokenizer.cls_token] + token_list + [tokenizer.sep_token]
        token_boxes = [[0,0,0,0]] + token_boxes + [[1000,1000,1000,1000]]
        
        input_ids = tokenizer.convert_tokens_to_ids(token_list)
        input_tensor = torch.tensor([input_ids])
        bbox_tensor = torch.tensor([token_boxes])
        
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)
        input_tensor = input_tensor.to(device)
        bbox_tensor = bbox_tensor.to(device)
        
        # 3. Inference
        with torch.no_grad():
            outputs = model(
                input_ids=input_tensor,
                bbox=bbox_tensor
            )
            
        # 4. Decode
        logits = outputs.logits
        preds = logits.argmax(-1).squeeze().tolist()
        if isinstance(preds, int): preds = [preds] # Handle single token case
        
        id2label = model.config.id2label
        
        # Realign to words (heuristic)
        # We just collect labels. A real system would align offset mappings.
        # For this pilot, we map back roughly.
        
        # Simplified: Just grab recognized entities
        fields = []
        seen_indices = set()
        
        # Note: token_list indexes map to preds indexes
        # We need to map token_list back to original words if we want perfect reconstruction
        # Let's just output the tokens tagged with meaningful labels
        
        # Or better: reconstruct string
        current_entity = {"label": None, "text": ""}
        
        for i, token in enumerate(token_list):
            if token in [tokenizer.cls_token, tokenizer.sep_token]:
                continue
                
            label_id = preds[i]
            label = id2label[label_id]
            
            clean_token = token.replace("##", "")
            
            if label != 'O':
                # Just append as a found field
                fields.append({
                    "label": label,
                    "text": clean_token,
                    "confidence": 0.9
                })

        # Consolidate '##' subwords
        # Simple concat for demo
        final_fields = []
        if fields:
            curr_label = fields[0]['label']
            curr_text = fields[0]['text']
            
            for f in fields[1:]:
                if f['label'] == curr_label:
                    curr_text += f['text']
                else:
                    final_fields.append({"label": curr_label, "text": curr_text, "confidence": 0.8})
                    curr_label = f['label']
                    curr_text = f['text']
            final_fields.append({"label": curr_label, "text": curr_text, "confidence": 0.8})

        return {"fields": final_fields}

    except Exception as e:
        print(f"Inference Error: {e}")
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)
