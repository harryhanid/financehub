import os, sys
sys.path.insert(0, '.')
import config
config.DB_PATH = os.path.join('tests', 'test_dash_reorder_render.db')
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

print('chart-card count (must stay 9):', body.count('beasiswa-dash-chart-card'))
print('grafik-grid count (was 3, now 5):', body.count('beasiswa-dash-grafik-grid'))
print('section-panel count (must stay 3):', body.count('class="beasiswa-dash-section-panel"'))

for cid in ['dash-chart-bulanan', 'dash-chart-tahunan', 'dash-monthly-table',
            'dash-chart-kategori', 'dash-kategori-table', 'dash-jenjang-table',
            'dash-pillar-year-table', 'dash-latest-payments-table', 'dash-program-table']:
    count = body.count('id="' + cid + '"')
    print(cid, 'count:', count)
    assert count == 1, cid + ' must appear exactly once'

breakdown_idx = body.index('Breakdown Realisasi')
program_idx = body.index('dash-program-table')
detail_idx = body.index('Detail Transaksi')
print('Program card is between Breakdown Realisasi and Detail Transaksi titles:', breakdown_idx < program_idx < detail_idx)

detail_panel = body[detail_idx:]
print('Detail Transaksi panel has exactly 1 chart-card:', detail_panel[:detail_panel.index('</details>')].count('beasiswa-dash-chart-card') == 1)

os.remove(config.DB_PATH)
