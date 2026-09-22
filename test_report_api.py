import urllib.request

try:
    req = urllib.request.Request("http://localhost:8081/beasiswa/sahabat/api/report?year=2027")
    req.add_header('Cookie', 'session=your_session_here') # I might not have auth
    with urllib.request.urlopen(req) as response:
        print(response.read())
except Exception as e:
    print(e)
