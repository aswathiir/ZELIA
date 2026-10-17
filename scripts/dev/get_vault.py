import requests
import json

hh = "391f4ba836df0711cd420c11d7ba041afddc1883eeab71856b6a7b92359238e8"
print("Karthik:")
resp = requests.get(f"http://localhost:8009/households/{hh}/workflow-status")
print(json.dumps(resp.json(), indent=2))
