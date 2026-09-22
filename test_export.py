import os, sys
sys.path.insert(0, os.path.abspath('app'))
from app import create_app
from database import init_db
from modules.etf_payment_application.service import export_pa_excel

init_db()
app = create_app()
with app.app_context():
    # company 1 is SMT, maybe try 1
    # or just try export_pa_excel
    res = export_pa_excel(1, 'combine', 'active')
    print('Export length:', len(res))
