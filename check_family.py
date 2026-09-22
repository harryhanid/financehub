from app.modules.sahabat_etf.service import get_family_summary
from app import create_app

app = create_app()
with app.app_context():
    try:
        f = get_family_summary(1, [2026], ["Semua"])
        print(len(f))
    except Exception as e:
        import traceback
        traceback.print_exc()
