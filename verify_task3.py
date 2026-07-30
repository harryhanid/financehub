import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_panel_render.db')
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
print('section-panel count:', body.count('class="beasiswa-dash-section-panel"'))
print('chart-card count (must stay 9):', body.count('beasiswa-dash-chart-card'))
print('old section-label gone:', 'beasiswa-dash-section-label' not in body)
os.remove(config.DB_PATH)
