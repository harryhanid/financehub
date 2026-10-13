"""Indonesian number formatting for the Management Report screens (1.234,5)."""


def id_number(value, decimals: int = 1) -> str:
    """1234.5 -> '1.234,5' (dot thousands, comma decimals); None -> ''."""
    if value is None:
        return ""
    s = f"{float(value):,.{decimals}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def id_percent(value, decimals: int = 1) -> str:
    """-0.791 -> '-79,1%'; None -> ''."""
    if value is None:
        return ""
    return id_number(value * 100, decimals) + "%"


def id_amount(value, decimals: int = 0) -> str:
    """Accounting style used by the HO Report: '-' for zero, parentheses for negatives."""
    if value is None or value == 0:
        return "-"
    if value < 0:
        return f"({id_number(-value, decimals)})"
    return id_number(value, decimals)
