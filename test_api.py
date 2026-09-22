import json
from app import create_app
from app.modules.sahabat_etf.service import get_yearly_breakdown

app = create_app()
with app.app_context():
    # Use company_id = 1 (or whatever is valid)
    try:
        yearly_data = get_yearly_breakdown(1)
        print(json.dumps(yearly_data, indent=2))
    except Exception as e:
        print("Error:", str(e))
