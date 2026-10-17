from PIL import Image, ImageDraw, ImageFont
import os

def create_sample_image():
    # Create white image
    img = Image.new('RGB', (800, 600), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    
    # We might not have a Tamil font on this Windows system or inside the container default.
    # We will fallback to basic English for the "Real" test if Tamil font fails, 
    # but the container has 'fonts-noto' or similar usually if we installed tesseract-ocr-tam.
    # Actually, generating the image LOCALLY (on Windows) is hard if the user doesn't have Tamil fonts.
    # Let's stick to English for the generated image to prove the PIPELINE works (Tesseract runs).
    # If the user has a real image, they can use that later.
    
    text_lines = [
        (20, 20, "GOVERNMENT OF TAMIL NADU"),
        (20, 60, "Name: Rajesh Kumar"),
        (20, 100, "Father Name: Senthil"),
        (20, 140, "DOB: 12-05-1985"),
        (20, 180, "Address: 123, Gandhi Road, Chennai")
    ]
    
    for x, y, text in text_lines:
        d.text((x, y), text, fill=(0, 0, 0))
        
    img.save("sample_form.jpg")
    print("Created sample_form.jpg")

if __name__ == "__main__":
    create_sample_image()
