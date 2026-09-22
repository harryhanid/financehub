import json
import urllib.request

req = urllib.request.Request("http://localhost:8081/beasiswa/sahabat/api/breakdown")
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(list(data.keys()))
except Exception as e:
    print(e)
