from format_utils import format_rupiah


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
