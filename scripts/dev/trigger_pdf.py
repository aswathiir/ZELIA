import requests

print("Triggering validation for Karthik 5 (309)")
r1 = requests.post("http://localhost:8009/submissions/309/validate-documents", json={"auto_correct_form": True}, headers={"x-user-role": "system"})
print("Status 309:", r1.status_code)
if r1.status_code == 200:
    print(r1.json().get('validated_at'))

print("Triggering validation for Anjali (313)")
r2 = requests.post("http://localhost:8009/submissions/313/validate-documents", json={"auto_correct_form": True}, headers={"x-user-role": "system"})
print("Status 313:", r2.status_code)
if r2.status_code == 200:
    print(r2.json().get('validated_at'))
