# Sponsorship Filter Style and Z-Index Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the Tahun (year) multi-select dropdown on Sponsorship's Data/Outstanding/Report tabs so its topmost option is never hidden behind the fixed header, and make its trigger button visually match the plain `<select>` filters next to it and in Payment Application.

**Architecture:** Two literal-value changes in `app/static/css/budget.css` — a `z-index` bump on the popover panel, and a full restyle of the trigger button to reuse the app's global `input, select, textarea` values. No template or JS changes; all three tabs share this one CSS file.

**Tech Stack:** CSS only. pytest for a static-asset content regression check (no frontend test framework exists in this codebase).

## Global Constraints

- Multi-year checkbox selection is preserved — no conversion to a native single-select `<select>`.
- Only `app/static/css/budget.css` and `app/tests/test_budget_routes.py` change.
- `.budget-dropdown-check`, `.budget-dropdown-content`'s non-`z-index` properties, and its label styles are unchanged — only `.budget-dropdown-content`'s `z-index` and all of `.budget-dropdown-btn`'s declarations change.

---

### Task 1: Fix z-index and restyle the Tahun dropdown button

**Files:**
- Modify: `app/static/css/budget.css:432-452`
- Test: `app/tests/test_budget_routes.py`

- [ ] **Step 1: Write the failing test**

Append to `app/tests/test_budget_routes.py`:

```python
def test_budget_css_dropdown_button_matches_global_input_style(client):
    login(client)
    resp = client.get("/static/css/budget.css")
    assert resp.status_code == 200
    css = resp.data.decode()
    assert "z-index: 101;" in css
    dropdown_btn_start = css.index(".budget-dropdown-btn {")
    dropdown_btn_block = css[dropdown_btn_start:dropdown_btn_start + 400]
    assert "var(--sl-300)" in dropdown_btn_block
    assert "var(--r-md)" in dropdown_btn_block
    assert "font-size: .8125rem;" in dropdown_btn_block
    assert "var(--bg-card)" not in dropdown_btn_block
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k dropdown_button_matches_global_input_style`
Expected: FAIL — `.budget-dropdown-content` is still `z-index: 10;` and `.budget-dropdown-btn` still uses `var(--bg-card)`/`var(--border-color)` instead of the global tokens.

- [ ] **Step 3: Apply the CSS fix**

In `app/static/css/budget.css`, replace:

```css
.budget-dropdown-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 8px;
  padding: 0.4rem 0.7rem;
  font-size: 0.85rem;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.budget-dropdown-content {
  display: none;
  position: absolute;
  background-color: var(--bg-card);
  min-width: 100%;
  box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
  z-index: 10;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
  margin-top: 4px;
}
```

with:

```css
.budget-dropdown-btn {
  background: #FFF;
  border: 1px solid var(--sl-300);
  color: var(--sl-900);
  border-radius: var(--r-md);
  padding: .375rem .6875rem;
  font-size: .8125rem;
  width: 100%;
  text-align: left;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-family: inherit;
  transition: border-color .12s, box-shadow .12s;
}
.budget-dropdown-btn:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(37,99,235,.09);
}
.budget-dropdown-content {
  display: none;
  position: absolute;
  background-color: var(--bg-card);
  min-width: 100%;
  box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
  z-index: 101;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  max-height: 200px;
  overflow-y: auto;
  margin-top: 4px;
}
```

(Only `.budget-dropdown-btn`'s declarations and `.budget-dropdown-content`'s
`z-index` change — the popover panel's own background/border/shadow/sizing
stay as they are, per the design's decision that only the trigger button
looked inconsistent.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v -k dropdown_button_matches_global_input_style`
Expected: PASS

- [ ] **Step 5: Run the full Budget test suite**

Run: `cd C:\Financehub\app && python -m pytest tests/test_budget_routes.py -v`
Expected: all PASS (same pre-existing exception as prior Budget plans, `test_nav_stays_visible_on_budget_pages`, already documented as stale).

- [ ] **Step 6: Manual check**

Open Sponsorship → Data. Click the Tahun filter button, confirm the
dropdown panel opens fully visible with no option hidden behind the
header — including the topmost year. Confirm the button's border/padding/
font now look identical to the Cat/Pillar/Description `<select>` filters
next to it. Pick 2+ years, confirm the table filters to their union
(multi-select still works). Repeat the same check on Outstanding and
Report (same CSS file, same widget). Compare visually against Payment
Application's filter row to confirm the styling now matches.

- [ ] **Step 7: Commit**

```bash
cd C:\Financehub
git add app/static/css/budget.css app/tests/test_budget_routes.py
git commit -m "fix: Sponsorship Tahun filter z-index and style consistency"
```
