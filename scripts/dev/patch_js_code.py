import re

with open("/tmp/live_n8n_code.js", "r") as f:
    code = f.read()

# Replace the pension1.pdf line
new_line = "  'pension1.pdf': { name: { page: 0, x: 380.0, y: 706.5, fontSize: 11.0 }, age: { page: 0, x: 480.0, y: 693.5, fontSize: 11.0 }, address: { page: 0, x: 380.0, y: 484.0, fontSize: 11.0 }, gender: { page: 0, x: 380.0, y: 656.5, fontSize: 11.0 } },"
code = re.sub(r"  'pension1\.pdf': \{.*\},", new_line, code)

with open("generate_pdf_code.js", "w") as f:
    f.write(code)

print("Created generate_pdf_code.js")
