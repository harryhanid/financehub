from modules.management_report.formatting import id_amount, id_number, id_percent


def test_id_number_uses_dot_thousands_and_comma_decimals():
    assert id_number(1234.5) == "1.234,5"
    assert id_number(1234567.891, 2) == "1.234.567,89"
    assert id_number(3200, 0) == "3.200"
    assert id_number(-731.8) == "-731,8"
    assert id_number(0) == "0,0"
    assert id_number(None) == ""


def test_id_percent():
    assert id_percent(-0.791045) == "-79,1%"
    assert id_percent(0.52) == "52,0%"
    assert id_percent(None) == ""


def test_id_amount_is_accounting_style_for_the_ho_report():
    assert id_amount(3200) == "3.200"
    assert id_amount(-97500) == "(97.500)"
    assert id_amount(0) == "-"
    assert id_amount(None) == "-"
    assert id_amount(1234.4) == "1.234"
