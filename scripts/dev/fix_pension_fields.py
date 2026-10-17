import json

path = "data/ingestion/field_map_top5_calibrated.json"
with open(path, "r") as f:
    data = json.load(f)

if "pension1.pdf" in data["templates"]:
    data["templates"]["pension1.pdf"]["fields"] = {
        "name": { "page": 0, "x": 380.0, "y": 706.5, "fontSize": 10, "required": True },
        "date_of_birth": { "page": 0, "x": 380.0, "y": 693.5, "fontSize": 10 },
        "age": { "page": 0, "x": 480.0, "y": 693.5, "fontSize": 10, "required": True },
        "father_name": { "page": 0, "x": 380.0, "y": 681.0, "fontSize": 10 },
        "gender": { "page": 0, "x": 380.0, "y": 656.5, "fontSize": 10, "required": True },
        "annual_income": { "page": 0, "x": 380.0, "y": 643.5, "fontSize": 10 },
        "address": { "page": 0, "x": 380.0, "y": 484.0, "fontSize": 9, "required": True },
        "aadhaar_number": { "page": 0, "x": 380.0, "y": 471.5, "fontSize": 10 },
        "phone": { "page": 0, "x": 380.0, "y": 508.5, "fontSize": 10 }
    }

with open(path, "w") as f:
    json.dump(data, f, indent=2)
print("Updated json!")
