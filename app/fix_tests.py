test_path = r"C:\Financehub\app\tests\test_beasiswa_routes.py"
with open(test_path, "r", encoding="utf-8") as f:
    t = f.read()

t = t.replace("from tests.test_beasiswa_routes import _login, _select_etf\n    _login(client)", "from tests.test_beasiswa_routes import login, _select_etf\n    login(client)")

with open(test_path, "w", encoding="utf-8") as f:
    f.write(t)

print("Fixed tests")
