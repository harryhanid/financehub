# Sponsorship Dashboard Amount Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop the "Rp" prefix from every amount on the Sinar Mas Tjipta → Sponsorship → Dashboard page, per `docs/superpowers/specs/2026-08-04-sponsorship-dashboard-amount-format-design.md`.

**Architecture:** One-line change to the single shared formatter every amount on this page already calls.

**Tech Stack:** Vanilla JS. No dependencies.

## Global Constraints

- Only `_sponsorshipFormatJutaan(n)` changes — millions-rounding and `toLocaleString("id-ID")` formatting stay exactly as-is, only the `"Rp " +` prefix is removed.
- No other Sponsorship tab (Data/Input/Report) is touched — they use `fmtRupiah`, a separate function.

---

### Task 1: Drop the "Rp" prefix

**Files:**
- Modify: `app/static/js/sponsorship.js:210-213`

- [ ] **Step 1: Edit the formatter**

Replace (current lines 210-213):

```javascript
function _sponsorshipFormatJutaan(n) {
  const jt = Math.round((n || 0) / 1000000);
  return "Rp " + jt.toLocaleString("id-ID");
}
```

with:

```javascript
function _sponsorshipFormatJutaan(n) {
  const jt = Math.round((n || 0) / 1000000);
  return jt.toLocaleString("id-ID");
}
```

- [ ] **Step 2: Manual verify**

Run the dev server, log in as Sinar Mas Tjipta, open Sponsorship → Dashboard. Confirm every amount (summary card, chart tooltips/labels, top-lembaga table, per-year table, per-category tables) shows a plain number in millions with no "Rp" prefix, and that the Data/Input/Report tabs are unaffected (still show full "Rp ..." amounts via `fmtRupiah`).

- [ ] **Step 3: Commit**

```bash
git add app/static/js/sponsorship.js
git commit -m "fix: drop Rp prefix from Sponsorship dashboard amounts"
```
