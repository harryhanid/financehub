# tests/test_branding_assets.py
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent


def test_style_css_has_flow_accent_gradient_tokens():
    css = (APP_DIR / "static" / "css" / "style.css").read_text(encoding="utf-8")
    assert "--accent:         #2D6ADF;" in css
    assert "--accent-2:       #0EA5C4;" in css
    assert "--accent:         #5B8CFF;" in css
    assert "--accent-2:       #22D3EE;" in css


def test_style_css_applies_gradient_only_at_hero_spots():
    css = (APP_DIR / "static" / "css" / "style.css").read_text(encoding="utf-8")
    assert "background: linear-gradient(135deg, var(--accent), var(--accent-2));" in css
    assert ".navbar-brand-icon {\n  width: 24px; height: 24px;\n  display: flex;" in css


def test_favicon_svg_exists_with_flow_gradient():
    favicon = (APP_DIR / "static" / "favicon.svg").read_text(encoding="utf-8")
    assert "#5B8CFF" in favicon
    assert "#22D3EE" in favicon
