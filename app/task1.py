import os

# 1. Create format_utils.py
format_utils_content = '''"""Shared number-formatting helpers. See
docs/superpowers/specs/2026-07-31-financehub-number-format-consistency-design.md
for why this exists: Python-side currency formatting was inconsistently using
en-US comma-thousands (f"{n:,.0f}") in some places and manually
.replace(",", ".")-corrected dot-thousands in others, across multiple modules.
"""


def format_rupiah(value, prefix: str = "Rp ") -> str:
    if value is None:
        return prefix + "0"
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        return prefix + "0"
    return prefix + f"{n:,.0f}".replace(",", ".")
'''
with open(r"C:\Financehub\app\format_utils.py", "w", encoding="utf-8") as f:
    f.write(format_utils_content)


# 2. Create tests/test_format_utils.py
test_content = '''from format_utils import format_rupiah


def test_format_rupiah_normal_value():
    assert format_rupiah(1234567) == "Rp 1.234.567"


def test_format_rupiah_zero():
    assert format_rupiah(0) == "Rp 0"


def test_format_rupiah_none():
    assert format_rupiah(None) == "Rp 0"


def test_format_rupiah_invalid_string():
    assert format_rupiah("not a number") == "Rp 0"


def test_format_rupiah_rounds_to_whole_rupiah():
    assert format_rupiah(1234567.6) == "Rp 1.234.568"


def test_format_rupiah_no_prefix():
    assert format_rupiah(1234567, prefix="") == "1.234.567"


def test_format_rupiah_custom_prefix():
    assert format_rupiah(1234567, prefix="") == "1.234.567"
    assert format_rupiah(1234567, prefix="IDR ") == "IDR 1.234.567"


def test_rupiah_jinja_filter_with_prefix(app):
    with app.app_context():
        tmpl = app.jinja_env.from_string("{{ 1234567 | rupiah }}")
        assert tmpl.render() == "Rp 1.234.567"


def test_rupiah_jinja_filter_without_prefix(app):
    with app.app_context():
        tmpl = app.jinja_env.from_string("{{ 1234567 | rupiah(false) }}")
        assert tmpl.render() == "1.234.567"


def test_rupiah_jinja_filter_handles_none(app):
    with app.app_context():
        tmpl = app.jinja_env.from_string("{{ none | rupiah }}")
        assert tmpl.render() == "Rp 0"
'''
with open(r"C:\Financehub\app\tests\test_format_utils.py", "w", encoding="utf-8") as f:
    f.write(test_content)


# 3. Modify app.py
app_py = r"C:\Financehub\app\app.py"
with open(app_py, "r", encoding="utf-8") as f:
    c = f.read()

old_block = '''    from modules.coming_soon.routes import coming_soon_bp
    app.register_blueprint(coming_soon_bp)

    @app.context_processor
    def inject_nav_modules():'''

new_block = '''    from modules.coming_soon.routes import coming_soon_bp
    app.register_blueprint(coming_soon_bp)

    from format_utils import format_rupiah
    app.jinja_env.filters["rupiah"] = lambda v, with_prefix=True: format_rupiah(v, "Rp " if with_prefix else "")

    @app.context_processor
    def inject_nav_modules():'''

c = c.replace(old_block, new_block)
with open(app_py, "w", encoding="utf-8") as f:
    f.write(c)

print("Task 1 complete")
