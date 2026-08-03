# FLOW Payment Memo — Persistent Bulk Selection Design (AGRI / APP / LAND)

## Problem

Following the same fix already shipped for Payment Application, the user asked to apply "selection survives across multiple name searches" to Payment Memo's AGRI, APP, LAND, and SETF pillar tabs.

Investigation showed the four tabs are NOT built on shared code (unlike Payment Application, where one mechanism serves all tabs) — each has its own independent selection implementation, in three different states:

- **AGRI (PAM, tab-pam):** two-level selection — checkboxes mark individual "beasiswa" payment lines (`pbId`) nested under a parent PAM record (`pamId`), tracked in `_pamBeasiswaSelected = { [pamId]: Set<pbId> }`. `loadPAM()` explicitly resets both `_pamBeasiswaSelected = {}` and `_pamBeasiswaCache = {}` on every search — this reproduces the reported bug (confirmed by the user: this is the tab they actually tested).
- **APP (FIORI, tab-fiori):** flat selection — a `Set` (`_fioriSelected`) plus a `Map` of `{label}` metadata. **Correction after deeper review:** `loadFIORI()` also explicitly calls `_fioriSelected.clear()` / `_fioriSelectionMeta.clear()` on every search (lines 2777-2778) — an initial pass only checked for `_fioriSelected = ...` reassignment and missed this `.clear()` call. APP has the same real data-loss bug as AGRI, just with a flat (not two-level) selection model.
- **LAND (SML, tab-sml):** same flat `Set`/`Map` shape as APP, but `loadSML()` genuinely never clears `_smlSelected`/`_smlSelectionMeta` — the only `.clear()` calls on these are in the manual "batal" button (`smlClearAllChips()`) and after a successful bulk update (`smlBulkUpdate()`), both intentional. The bulk-bar/chips already read from these persistent structures, not DOM `:checked` state. The only gap: when a previously-selected row reappears in a later search's re-rendered `tbody`, its new checkbox is always rendered unchecked (no `checked` attribute or row-highlight applied at render time), even though the underlying Set/Map still holds the selection correctly.
- **SETF (tab-setf):** has no bulk-select/checkbox UI at all today. Confirmed out of scope per user — building a new feature is a different ask than fixing persistence.

## Scope (confirmed with user)

- Fix AGRI's real data-loss bug (selection state gets wiped on every search).
- Fix APP's real data-loss bug (same root cause as AGRI — `loadFIORI()` clears selection on every search — found during a closer re-check after initial approval; folded into the same "real fix" category as AGRI rather than treated as cosmetic).
- Fix LAND's cosmetic gap (selection already persists correctly; checkboxes just don't visually restore on re-render).
- SETF: out of scope, no bulk-select feature exists there and none will be added by this work.

## Design

### AGRI (PAM) — stop wiping selection, decouple chip names from the row cache

**Stop resetting `_pamBeasiswaSelected` in `loadPAM()`.** Currently `loadPAM()` sets `_pamBeasiswaSelected = {}` unconditionally on every search; remove that line so the selection Set-of-Sets survives across searches, matching how FIORI/SML already behave.

**Keep resetting `_pamBeasiswaCache = {}`** (the cache of a PAM's fetched beasiswa lines) — this is fine to drop on each search to avoid unbounded memory growth. But `_agriAllChipsHtml()` currently depends on `_pamBeasiswaCache[pamId]` to look up a selected line's display name — once the cache is cleared for a PAM the user searched away from, its chip would lose its name. To decouple these, add a new flat map `_pamBeasiswaSelectionMeta` (`Map<pbId, {pamId, nama}>`), populated at the moment a checkbox is checked (in `agriToggleCheckbox` and the pending-select-all restore path in `agriFetchBeasiswaLines`), read from the just-fetched row data (`_pamBeasiswaCache[pamId]` at that moment, before it might later be cleared). `_agriAllChipsHtml()` is changed to read names from this meta map instead of re-deriving them from the (possibly-cleared) cache. `agriRemovePaChip`/`agriClearAll` also clean up the corresponding meta entries.

**Restore checked state on expand.** `agriFetchBeasiswaLines(masterTr, toggleEl, pamId)` currently only auto-checks all newly-rendered sub-line checkboxes when `_pamPendingSelectAll[pamId]` is true (an explicit "select all children" intent set before the lines were loaded). Extend this: after rendering the fetched lines, additionally check any row whose `pbId` is already present in `_pamBeasiswaSelected[pamId]` (a normal partial selection carried over from before this search), not just the all-or-nothing pending-select-all case.

**Master row indeterminate state before expand.** When AGRI's master PAM rows re-render from a new search (`_agriRenderPage()`), a PAM whose `_pamBeasiswaSelected[pamId]` has any entries should show its own checkbox (`pam-cb-<pamId>`) as `indeterminate = true` even before the user expands it — a "something in here is selected" signal. Full checked-vs-indeterminate resolution (comparing selected count to total line count) still only happens once expanded and `_syncPamCheckbox()` runs against the real DOM sub-rows, same as today.

**Clear behavior unchanged.** `agriClearAll()` (the "✕ Batal" button) continues to clear everything, now also clearing `_pamBeasiswaSelectionMeta`.

### APP (FIORI) — stop wiping selection, restore checkbox visual state

**Stop resetting `_fioriSelected`/`_fioriSelectionMeta` in `loadFIORI()`.** Remove the `_fioriSelected.clear()` / `_fioriSelectionMeta.clear()` lines from `loadFIORI()` so the flat Set/Map survive across searches. Since APP's model is already flat (no per-PAM sub-line grouping, no cache-dependent chip names), no equivalent of AGRI's separate selection-meta map is needed — `_fioriSelectionMeta` already stores `{label}` directly at select time, independent of any row cache.

**Restore checkbox visual state at render time.** In `loadFIORI()`'s row-rendering template string, check `_fioriSelected.has(r.id)` and, if true, render the checkbox with the `checked` attribute and the same inline highlight style (`background:#eff6ff`) that `fioriToggleCb` applies when a user checks a box interactively — so a row that reappears after a search looks exactly like it would if the user had just clicked it.

### LAND (SML) — restore checkbox visual state at render time only

No change to the underlying `_smlSelected`/`_smlSelectionMeta` — they already persist correctly (never cleared by `loadSML()`) and the bulk-bar/chips already read from them.

Change only the row-rendering template string in `loadSML()`: check `_smlSelected.has(r.id)` and, if true, render the checkbox with `checked` plus the same highlight styling (`background:#eff6ff` and the extra cell styling) that `smlToggleCb` applies interactively.

## Out of scope

- SETF: no bulk-select feature added.
- Any change to the `bulk-update`/`days-of-pam/bulk-update` API endpoints — both already accept arbitrary id lists; only client-side selection bookkeeping changes.
- Cross-tab selection sharing (AGRI's selection is independent from APP/LAND's, as it already is today via separate variables) — not requested, not built.
- Persisting selection beyond the current page session (Payment Memo never navigates away for search/filter, so there is no reload to survive — an in-memory JS variable, not sessionStorage, is sufficient here, unlike Payment Application which does full page reloads).
