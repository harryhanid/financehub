# Auto-Focus Search Box on Filter Panel Open — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After the filter panel opens (via the `F` keyboard shortcut or a mouse click on the Filter button) in Beasiswa, Payment Approval Memo, or ETF Payment Application, keyboard focus moves straight into the panel's search textbox on desktop/pointer devices — no mouse click needed to start typing.

**Architecture:** One change to the existing shared `toggleFilterPanel(panelId, btnId)` function in `app.js` — the same function ETF PA calls directly and Payment Memo/Beasiswa call through via `toggleActiveTabFilter()`. When the panel transitions closed→open, and `window.matchMedia("(hover: hover) and (pointer: fine)")` matches (desktop/pointer device, not touch), it finds the first `input[type="text"]` inside the panel and calls `.focus()` on it. No per-module template changes.

**Tech Stack:** Vanilla JS (matches `app.js` conventions). No new dependencies, no test framework for frontend behavior in this repo — verification is manual via the dev server, same approach as the 2026-07-13 keyboard-shortcuts plan this feature extends.

## Global Constraints

- Design spec: `docs/superpowers/specs/2026-07-27-filter-search-autofocus-design.md` — this plan implements it in full.
- Only fires on the closed→open transition. Closing the panel must never move focus.
- Desktop/pointer devices only — gated by `window.matchMedia("(hover: hover) and (pointer: fine)").matches`. Must not fire on touch devices (this is what avoids popping the on-screen keyboard unexpectedly).
- Targets the first `input[type="text"]` inside the just-opened panel. If none exists, do nothing — no error.
- Scope is exactly the same 3 templates the original `F` shortcut covers: `beasiswa/index.html`, `payment_memo/index.html`, `etf_payment_application/index.html` — but this task touches **zero** templates, only `app.js`, since all three already funnel through `toggleFilterPanel`.
- Dev server (template/static auto-reload — `app.js` changes need a hard browser refresh, Ctrl+Shift+R, since it's a static file):
  ```
  cd C:\Financehub\app && C:\Users\25010160\AppData\Local\Python\pythoncore-3.14-64\python.exe -m flask --app app:create_app run --port 5051 --debug
  ```
  Login credentials are required to reach these modules — if not available in the execution environment, ask the user for dev credentials before starting manual verification; do not guess or brute-force credentials.
- Chrome DevTools' device-toolbar/touch-emulation mode flips the `pointer`/`hover` media features to touch values — this is the mechanism used to verify the touch-skip behavior without a physical touch device.

---

### Task 1: Auto-focus the search input in `toggleFilterPanel()`

**Files:**
- Modify: `C:\Financehub\app\static\js\app.js:435-441`

**Interfaces:**
- Consumes: existing `.filter-bar.collapsible` / first-`input[type="text"]` convention, already present unmodified in all three templates (confirmed by audit in the design spec — every filter panel's first text input is its search box, no exceptions).
- No new exports — `toggleFilterPanel` and `toggleActiveTabFilter`'s existing call signatures are unchanged, so no other file needs to change.

Current code (`app.js:435-441`):

```js
function toggleFilterPanel(panelId, btnId) {
  const panel = document.getElementById(panelId);
  const btn = document.getElementById(btnId);
  if (!panel) return;
  const open = panel.classList.toggle("open");
  if (btn) btn.classList.toggle("active", open);
}
```

- [ ] **Step 1: Add the auto-focus behavior**

Replace the block above with:

```js
function toggleFilterPanel(panelId, btnId) {
  const panel = document.getElementById(panelId);
  const btn = document.getElementById(btnId);
  if (!panel) return;
  const open = panel.classList.toggle("open");
  if (btn) btn.classList.toggle("active", open);
  if (open && window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
    const searchInput = panel.querySelector('input[type="text"]');
    if (searchInput) searchInput.focus();
  }
}
```

- [ ] **Step 2: Syntax check**

Run: `cd C:\Financehub && node --check app/static/js/app.js`
Expected: no output, exit code 0 (this repo has no JS test framework — a syntax check is the automated verification available, same as the 2026-07-13 keyboard-shortcuts plan).

- [ ] **Step 3: Manual verification — desktop, all three modules**

Start the dev server (see Global Constraints), log in with a real account, and check each module. Use a normal (non-touch-emulated) browser window for this step.

**Beasiswa** (`/beasiswa/`):
1. Click into any tab that has a filter panel (e.g. "Data Payment"), so its filter panel exists in the DOM.
2. Click somewhere neutral (not inside any input), press `F`. Confirm: the filter panel opens AND the "Cari / Kata Kunci" textbox shows a visible blinking caret (focused) with no click.
3. Type a few characters — confirm they land in that textbox and the list filters as expected (existing `oninput` behavior unaffected).
4. Press `F` again to close the panel — confirm no error in the browser console and focus does not jump anywhere unexpected.
5. Click the Filter button directly with the mouse (instead of pressing `F`) — confirm the same auto-focus happens.
6. Repeat steps 2–5 on at least one other tab with its own filter panel (e.g. "Data Siswa" or "Rekam Medis") to confirm it's not just the first panel that works.

**Payment Approval Memo** (`/payment-memo/`):
1. Repeat steps 2–5 above on a tab with a filter panel (e.g. Draft Pay or PAM).

**ETF Payment Application** (`/etf-payment-application/`):
1. Repeat steps 2–5 above on a tab with a filter panel (e.g. AGRI).

- [ ] **Step 4: Manual verification — touch-emulated, one module**

In Chrome DevTools, open the device toolbar (Ctrl+Shift+M) and select a touch device profile (e.g. "iPhone 14"). Reload the page.

On Beasiswa's "Data Payment" tab: tap the Filter button (or use the `F` key via the emulated device's keyboard if available) to open the panel. Confirm the search textbox does **not** receive focus automatically (no blinking caret without an explicit tap into the field). Confirm the panel still opens/closes normally and the field is still tappable and usable manually.

Turn off device emulation when done.

- [ ] **Step 5: Commit**

```bash
cd C:\Financehub
git add app/static/js/app.js
git commit -m "feat: auto-focus filter search box on panel open (desktop only)"
```

---

## Self-Review

**Spec coverage:** All 6 Decisions rows in the design spec map to this single task — which input gets focus (Step 1's selector), device scope (Step 1's `matchMedia` guard + Step 4's verification), when focus moves (Step 1's `open &&` guard + Step 3.4's close-check), shared-function implementation (Step 1 touches only `app.js`), trigger-agnostic (Step 3.5 verifies mouse-click parity), missing-input safety (Step 1's `if (searchInput)` guard — no explicit test since the spec confirms no panel currently lacks a search input, but the guard itself prevents a crash if that ever changes).

**Placeholder scan:** No TBD/TODO; the code change is given in full, both before and after; every verification step has explicit expected outcomes.

**Type/name consistency check:** N/A — this task doesn't introduce any new function, variable, or interface consumed elsewhere; it's a pure behavioral addition inside an existing function whose signature is unchanged.
