# Sponsorship Dashboard — Amount Format (Drop "Rp" Prefix)

## Problem

On Sinar Mas Tjipta → Sponsorship → Dashboard, every amount is prefixed
with "Rp" (e.g. "Rp 608"). The user wants plain numbers, still expressed
in millions (jutaan) as today, just without the currency prefix.

## Scope

All amount displays on the Sponsorship Dashboard route through one shared
helper, `_sponsorshipFormatJutaan(n)` in `app/static/js/sponsorship.js`
(lines 210-213) — used by the summary stat card, chart tooltips/labels,
the top-lembaga table, the per-year table, and the per-category tables.
No other page/tab is affected (Sponsorship's Data/Input/Report tabs use a
different formatter, `fmtRupiah`, not touched by this change).

## Design

`_sponsorshipFormatJutaan(n)` drops the `"Rp " +` prefix from its return
value. Rounding to millions and Indonesian locale thousands-separator
formatting (`toLocaleString("id-ID")`) stay exactly as-is — only the
currency-symbol prefix is removed. Since every amount on this page
already calls this one function, the fix applies everywhere at once with
no other call sites needing changes.

## Out of Scope

- Any other Sponsorship tab (Data, Input, Report) — those use `fmtRupiah`,
  a separate function, untouched.
- Any other module's dashboard or amount formatting.
- Changing the millions-rounding or locale-formatting behavior itself.
