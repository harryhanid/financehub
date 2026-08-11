# Design: Sahabat ETF Laporan — Populate the Periode Column

**Date:** 2026-08-11
**Module:** Finance Hub — Eka Tjipta Foundation / Beasiswa / Sahabat ETF / Laporan
**Status:** Approved

---

## Summary

The Sahabat ETF report (Excel export and the on-screen Laporan tab, both backed by `build_report_data()`) has a "Periode" column that was deliberately left blank in the original design — there was no source data for a student's program duration at the time. This adds that data: **Periode is derived from `siswa.angkatan` (entry year) plus a duration determined by the row's jenjang (PENDIDIKAN) or a flat 1 year (KESEHATAN)**, computed live, not stored.

## Decisions

| Question | Decision |
|---|---|
| Periode formula (PENDIDIKAN) | `angkatan` to `angkatan + durasi`, where durasi comes from a jenjang lookup table: SD=6, SMP=3, SMA=3, SMK=3, S1=4, S2=2, S3=4 |
| Periode formula (KESEHATAN) | `angkatan` to `angkatan + 1`, regardless of jenjang — same source field (`angkatan`), just a fixed 1-year duration |
| Missing/unmapped data | If `angkatan` is null, or the row's jenjang isn't in the duration table, Periode is left blank (matches today's behavior — no crash, no guess) |
| Which rows get Periode | Only individual siswa detail rows (per jenjang/kategori group). Subtotal, section-total, recap, combined-total, grand-total, and pillar-breakdown rows stay blank — Periode is a per-siswa attribute, and recap/total rows already leave the Pillar column blank for the same reason (no single unambiguous value to show once rows are merged) |
| Scope | Both the Excel export (`report_xlsx.py`) and the on-screen Laporan tab (`sahabat_etf.js`) — the on-screen tab currently has no Periode column at all and gains one |
| Storage | Not persisted anywhere — computed on the fly inside `build_report_data()` from `siswa.angkatan` + `siswa.jenjang`, same as every other derived value in this report |

---

## Architecture

### File changes

- **Modify:** `app/modules/sahabat_etf/service.py` — `_fetch_report_rows()` gains `s.angkatan` in both SELECT queries; `_build_buckets()` carries `angkatan` through each bucket; `_build_section()` computes `periode_start`/`periode_end` per siswa row via a new `_compute_periode()` helper.
- **Modify:** `app/modules/sahabat_etf/report_xlsx.py` — `_write_section()`'s siswa-row loop writes `periode_start` to column C and `periode_end` to column E (D already shows the static "-" from the header's merged cell area, per the original Book3.xlsx-derived column layout) when both values are present; leaves C/D/E blank otherwise (already blank today by omission).
- **Modify:** `app/static/js/sahabat_etf.js` — `setfLaporanHeaderRow()` gains a "Periode" `<th>`; `setfLaporanNamaRow()` gains a Periode `<td>` showing `"{periode_start} - {periode_end}"` when present, blank otherwise; `setfLaporanLabelRow()` (used for subtotal/total rows) gains a matching blank Periode `<td>` to keep column count consistent.

No changes to `build_report_workbook()`'s or `setfRenderLaporanSection()`'s overall structure/row ordering, no changes to any other section of the report, no schema/migration — `siswa.angkatan` already exists and is already used elsewhere in this module.

### Periode computation

```python
_JENJANG_DURASI = {"SD": 6, "SMP": 3, "SMA": 3, "SMK": 3, "S1": 4, "S2": 2, "S3": 4}
_KESEHATAN_DURASI = 1

def _compute_periode(section_key: str, jenjang: str, angkatan) -> tuple:
    if not angkatan:
        return None, None
    if section_key == "KESEHATAN":
        return angkatan, angkatan + _KESEHATAN_DURASI
    durasi = _JENJANG_DURASI.get(jenjang)
    return (angkatan, angkatan + durasi) if durasi else (None, None)
```

For PENDIDIKAN rows, `jenjang` is the group's own key (SD/SMA/S1/S2/etc. — already the grouping dimension for that section, no new lookup needed). For KESEHATAN rows, the jenjang argument is irrelevant to the formula but the siswa's own `angkatan` is still the source year.

### Excel column reuse

`report_xlsx.py` already defines `_COL["periode_start"] = "C"` and `_COL["periode_end"] = "E"` (from the original Book3.xlsx-derived layout) but nothing writes to them today. This change starts writing to those two existing column slots for siswa rows only — no new columns, no header changes (the merged "Periode" header spanning C:E already exists).

---

## Testing

- Unit tests for `_compute_periode()` covering: PENDIDIKAN with a known jenjang (e.g. S1 → angkatan+4), KESEHATAN (angkatan+1 regardless of jenjang), missing angkatan (returns `None, None`), unmapped jenjang (returns `None, None`).
- Integration test on `build_report_data()`: seed a siswa with a known `angkatan` and jenjang, confirm the resulting siswa row carries the expected `periode_start`/`periode_end`, and that subtotal/total/recap entries do not carry those keys (or carry `None`).
- `report_xlsx.py`: extend existing openpyxl-based tests to assert C/E cell values for a siswa row with known periode, and that they're blank for a siswa row with no angkatan.
- No frontend test framework for the JS side — verified via the existing force-render/structural-check pattern (assert the new `<th>Periode</th>` is present) plus a manual browser check if available.
- Full Python regression suite run once at the end.

## Out of Scope

- Any UI to manually override/edit a computed Periode (still fully derived, not editable).
- Backfilling or storing Periode anywhere — stays a computed value.
- Handling SMP/SMK/S3 with real data validation (no current students in those jenjang — the duration table entries are there for completeness/forward-compatibility, not tested against real records).
- Any change to the Excel/on-screen report's other columns or sections.
