# FLOW Filter Panel — Persist Open State Across Reload — Design

## Problem

Three modules (Beasiswa, Payment Memo, Payment Application) have a collapsible
filter panel per data tab (`.filter-bar.collapsible`), opened with `F` and
closed with `Esc` (as of commit `4df799c`, which removed the old visible
Filter/Full Screen toggle buttons in favor of pure keyboard control — no
button exists anymore).

Roughly a dozen save/update actions across these three modules call
`location.reload()` (directly, or via `setTimeout(() => location.reload(),
800)`) after a successful save, to refresh the displayed data — e.g. Payment
Memo's "Simpan Tanggal Bayar" flow. A full page reload wipes all client-side
DOM state, including the filter panel's `.open` class, since it has never
been persisted anywhere. The user opens the filter, sets values, triggers a
save, and the filter silently closes — even though a save is not one of the
actions that should close it (only pressing `Esc` or switching to a different
tab should).

## Goal

Filter panel open/closed state survives a same-tab `location.reload()`, while
still correctly closing on:
- `Esc` (already implemented, must keep working identically)
- Switching to a different tab within the same module (already implemented,
  must keep working identically)
- Navigating to a different module (naturally correct — new page, nothing to
  restore)

## Current Mechanism (post `4df799c`)

- `F` (global `keydown` listener in `app.js`) → `getActiveFilterPanel()` then
  `panel.classList.add('open')`. No button, no badge — purely a class toggle.
- `Esc` (same listener) → `getActiveFilterPanel()` then
  `panel.classList.remove('open')`.
- Switching tabs (`initTabs()`'s per-button click listener) →
  `container.querySelectorAll(".filter-bar.collapsible.open").forEach(p =>
  p.classList.remove("open"))` — force-closes any open filter panel in the
  container as an unconditional side effect of every tab click.
- **Every page load also fires a tab click**: `initTabs()` ends by calling
  `requested.click()` (deep-linked via `?tab=`) or `tabs[0].click()` — this is
  the same click path used for genuine user tab-switches, so the force-close
  above runs on *every* load, including a same-tab reload. Any restore logic
  must run **after** this auto-activation click, not before or during —
  otherwise it fires, then gets immediately wiped by the very same init pass.
- Each filter panel has a **stable**, hand-written `id` in its template
  (`bsw-filter-siswa`, `bsw-filter-budget`, `bsw-filter-payment`,
  `bsw-filter-rekam` for Beasiswa; `pam-filter-draft-pay`, `pam-filter-pam`,
  `pam-filter-fiori`, `pam-filter-sml`, `pam-filter-smt`,
  `pam-filter-advance`, `pam-filter-setf`, `pam-filter-pa-advance`,
  `pam-filter-vendors` for Payment Memo; `pa-filter-panel`, reused across all
  of Payment Application's data tabs since each tab is a full page render).
  No randomly-generated IDs are involved (that fallback existed in the old
  `toggleActiveTabFilter()`, which `4df799c` deleted).

## Design

Persist via `sessionStorage`, keyed by the filter panel's own stable `id`:

- **On open** (`F` key adds `.open`): also
  `sessionStorage.setItem('fh-filter-open:' + panel.id, '1')`.
- **On close** — both close paths (`Esc`, and the tab-switch force-close
  loop) — also remove the corresponding `sessionStorage` entry for whichever
  panel(s) just lost `.open`.
- **On page load**: after `initTabs()` (and its internal auto-activation
  click) has fully run, check `sessionStorage` for the entry matching the
  *now-active* tab's filter panel (via the same `getActiveFilterPanel()`
  helper already used by the `F`/`Esc` handlers); if present, add `.open`
  back.

`sessionStorage` is scoped to the browser tab and cleared when it closes —
appropriately short-lived (this is transient UI state, not something that
should resurrect days later in a fresh session), and unlike a URL query
param it doesn't clutter shareable links or collide with the filter *value*
params some of these pages already carry.

### Why this doesn't need a page-identity prefix in the key

Every filter panel's `id` is already unique within a page. Between different
modules, the browser's `sessionStorage` is shared per-origin but the panel
IDs across modules don't collide (`bsw-*` vs `pam-*` vs `pa-filter-panel`),
and a stale entry from a different module (e.g. `pa-filter-panel` left
"open" from Payment Application, later visiting Payment Memo) is harmless
because `getActiveFilterPanel()` only ever looks up the panel that actually
exists in the current page's DOM — a key with no matching element on the
current page is simply never read.

### What does not change

- `Esc` and `F` behavior, exactly as `4df799c` left them.
- Tab-switch force-closing filter panels — unchanged, still fires on every
  click including auto-activation.
- No visible button, no badge, no Full Screen mode — none of that is being
  reintroduced.
- No template changes — this is entirely a `app.js` change.

## Testing

No existing automated test covers filter-panel open/close behavior (it's
pure client-side JS with no server-rendered assertions to hook). Verification
is manual browser smoke-testing across all three modules: open filter → set a
value → trigger a save that reloads → confirm filter is still open with the
same tab active; then confirm `Esc` still closes it and switching tabs still
closes it (and that state doesn't leak back if you return to that tab later
in the same session — i.e. confirm the close paths actually clear their
`sessionStorage` entries, not just the `.open` class).

## Out of Scope

- Budget, Bank, Sponsorship, Users — none of these have a collapsible filter
  panel; their filters are always-visible, nothing to persist.
- Converting the ~12 reload-after-save call sites to AJAX-only refresh
  (would eliminate the reload entirely, which is the more "ideal" long-term
  fix, but is a much larger, riskier refactor touching business logic across
  three modules, disproportionate to this specific complaint).
- Any change to what triggers reload after save — those stay as-is.
