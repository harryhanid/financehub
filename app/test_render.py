import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_status_badge_render.db')
if os.path.exists(config.DB_PATH): os.remove(config.DB_PATH)
from database import init_db
init_db()
from app import create_app
app = create_app(testing=True)
client = app.test_client()
login = client.post('/auth/login', json={'username':'admin','password':'Admin@123'})
assert login.get_json()['ok'], login.get_json()
client.post('/select-company', data={'company_id': 2})
resp = client.get('/beasiswa/')
print('STATUS', resp.status_code)
body = resp.data.decode('utf-8', errors='replace')
print('Status column header present:', '<th>Status</th>' in body)
print('colspan=6 fallback present:', 'colspan="6"' in body)
print('colspan=5 fallback gone:', 'colspan="5"' not in body.split('id="dash-latest-payments-table"')[1][:400])
os.remove(config.DB_PATH)
