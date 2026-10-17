import pytesseract
from PIL import Image, ImageDraw, ImageFont
import sys
import os

def test_ocr():
    print("Running Internal OCR Test (Verbose)...")
    
    # Create a dummy image if none exists
    img_path = "test_image.png"
    if not os.path.exists(img_path):
        print("Creating dummy image with text...")
        try:
            # Import removed from here to use global 'Image'
            img = Image.new('RGB', (400, 100), color = (255, 255, 255))
            d = ImageDraw.Draw(img)
            # Default font
            d.text((10,10), "ZELIA", fill=(0,0,0))
            img.save(img_path)
        except Exception as e:
            print(f"Failed to create image: {e}")
            sys.exit(1)

    # Check Tesseract version
    try:
        version = pytesseract.get_tesseract_version()
        print(f"Tesseract Version: {version}")
    except Exception as e:
        print(f"Failed to get version: {e}")

    # Run OCR
    print("Starting OCR (image_to_string)...")
    try:
        # Explicitly use English and standard config
        text = pytesseract.image_to_string(Image.open(img_path), lang='eng')
        print(f"OCR Raw Output: {text!r}")
        
        if "ZELIA" in text:
            print("SUCCESS: OCR recognized text.")
        else:
            print("WARNING: OCR ran but text output was unexpected.")
            
    except Exception as e:
        print(f"ERROR: OCR Engine Failed. {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_ocr()
