import fitz

doc = fitz.open("dataset/govt/templates/pension1.pdf")
page = doc[0]
blocks = page.get_text("dict")["blocks"]
coords = []
for b in blocks:
    if "lines" in b:
        for l in b["lines"]:
            text = "".join([s["text"] for s in l["spans"]]).strip()
            if len(text) > 3:
                # calc Y from bottom
                y_bottom = page.rect.height - l["bbox"][3]
                coords.append((text, round(y_bottom, 1)))

coords.sort(key=lambda x: -x[1])
for t, y in coords:
    print(f"y={y}: {t}")
