"""Shared number-formatting helpers. See
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
