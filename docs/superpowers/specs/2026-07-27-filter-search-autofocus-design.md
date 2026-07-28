# Design: Auto-Focus Search Box on Filter Panel Open

**Date:** 2026-07-27
**Module:** Finance Hub — Beasiswa, Payment Approval Memo, ETF Payment Application (all `.filter-bar.collapsible` modules)
**Status:** Approved

---

## Summary

Pressing `F` (or clicking the Filter button) already opens/closes the collapsible filter panel via the existing keyboard-shortcuts feature (`docs/superpowers/specs/2026-07-13-financehub-keyboard-shortcuts-design.md`), but the user still has to reach for the mouse to click into the search textbox afterward. This closes that gap: on desktop/pointer devices, opening the panel also moves keyboard focus straight into its first search textbox, so `F` → type is a fully keyboard-driven flow with no mouse needed. On touch devices, this is skipped entirely — focusing a text input on a touchscreen triggers the on-screen virtual keyboard, which is not wanted here since the point is speeding up a physical-keyboard/mouse-cursor workflow, not summoning a touch keyboard the user didn't ask for.

## Decisions

| Question | Decision |
|---|---|
| Which input gets focus? | The first `input[type="text"]` inside the panel that was just opened. Confirmed by direct file audit: in every `.filter-bar.collapsible` panel across all three modules (Beasiswa: 4 panels, Payment Memo: 3 panels, ETF Payment Application: 3 panels), the search textbox is always the first text input in the panel — no exceptions. |
| Device scope | Desktop/pointer devices only, via `window.matchMedia('(hover: hover) and (pointer: fine)').matches`. Skipped on touch devices (phones, tablets, touch-only laptops) so the on-screen keyboard never pops up automatically — a user on those devices still opens the panel via `F`/tap and taps the search box manually, same as today. |
| When does focus move? | Only on the open transition (panel going from closed → open). Closing the panel never moves focus anywhere. |
| Where is this implemented? | A single shared function, `toggleFilterPanel(panelId, btnId)` in `app.js` — the same function ETF PA calls directly and Payment Memo/Beasiswa call through via `toggleActiveTabFilter()`. One change covers all three modules; no per-module template edits needed, consistent with how the original `F` shortcut itself was implemented (per §2.3 of the 2026-07-13 spec: "the shortcut feature adds zero new per-module logic"). |
| Trigger-agnostic | Applies whether the panel is opened via the `F` keyboard shortcut or a direct mouse click on the Filter button — both paths call the same `toggleFilterPanel`, so there's no special-casing needed to distinguish them. |
| Missing search input | If a panel has no `input[type="text"]` (not observed in the current audit, but handled defensively), the function does nothing extra — no error, no focus change. |

## Architecture

**Modify `C:\Financehub\app\static\js\app.js`, `toggleFilterPanel(panelId, btnId)`:**

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

No changes to `toggleActiveTabFilter()` — it already delegates to `toggleFilterPanel()`, so the new behavior flows through automatically.

No changes to any template (`beasiswa/index.html`, `payment_memo/index.html`, `etf_payment_application/index.html`) — the fix lives entirely in the one shared JS function.

## Non-Goals

- No change to the `F` key binding, `Alt+←/→` tab-stepping, or any other existing shortcut behavior.
- No change to filter panels outside the `.filter-bar.collapsible` pattern (Bank, Budget, Users modules use a different, always-visible filter UI with no toggle button — `F` doesn't target them today and this change doesn't extend it there).
- No `scrollIntoView()` handling — the browser's native focus-triggered scroll behavior is relied on as-is; not overridden.
- No new visible UI (no additional hint text beyond the existing `<kbd>F</kbd>` badge from the original shortcuts feature).

## Testing

No backend changes. Verification is behavioral, via Flask test client + jsdom-style assertions are not practical for `matchMedia`/`focus()` in the existing pytest suite (no headless-browser test infra in this codebase, consistent with how the original keyboard-shortcuts feature and prior UI features here were verified). Verify manually in-browser instead:
- Desktop viewport: press `F` in each of the three modules (Beasiswa, Payment Memo, ETF Payment Application) and confirm the search textbox has visible focus (blinking caret) immediately after the panel opens, with no click needed.
- Confirm pressing `F` again (closing the panel) does not throw and does not move focus anywhere unexpected.
- Confirm clicking the Filter button with the mouse produces the same auto-focus result as pressing `F`.
- Resize/emulate a touch device (or use browser devtools' touch emulation, which flips `pointer`/`hover` media features) and confirm focus does **not** move automatically in that mode.
