from app.modules.sahabat_etf.service import get_pillar_breakdown, get_kategori_breakdown, get_yearly_breakdown
from app import create_app
app = create_app()
with app.app_context():
    print("PILLAR:")
    p = get_pillar_breakdown(1, [2026], ["Semua"])
    print(p)
    print("YEARLY:")
    y = get_yearly_breakdown(1, [2026], ["Semua"])
    print(y)
