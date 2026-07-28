# Design: FLOW Company Select → Dashboard Transition

**Date:** 2026-07-28
**Module:** FLOW — Company Select (`/select-company`) → Dashboard (`/dashboard`)
**Status:** Approved

---

## Summary

Extends the "seamless flow" narrative already built for login → company-select one hop further: after clicking Sinar Mas Tjipta or Eka Tjipta Foundation, the FLOW wordmark visually shrinks from its large centered position on the company-select page into its small navbar position on the Dashboard, instead of a hard page cut. Unlike the login → company-select transition, this one does **not** carry the ambient chart forward — Dashboard is a data-dense working page (stat cards, tables), and the earlier design already established that glassmorphism/ambient motifs stay off pages where they'd compete with reading dense data. The only two things that change here: the wordmark morphs, and Dashboard's dark/light mode follows the same dark canvas the user just came from — but only on a genuinely first visit (no saved theme preference yet), never overriding an explicit choice the user already made.

---

## Decisions

| Question | Decision |
|---|---|
| Dark/light continuity | If `localStorage['fh-theme']` is unset (user has never chosen a theme), set it to `'dark'` at the moment of company selection (client-side JS, right before the form submits — same point where the existing click flourish already runs). Dashboard's *existing* inline theme-detection script in `base.html` reads this on next load with zero changes needed there. If the user has already picked a theme before (dark or light), it is never overridden. |
| What visually continues | Only the FLOW wordmark (icon + text). It uses the View Transitions API to morph from its large centered position on company-select into its small position in Dashboard's navbar. No ambient chart, no accent-color flourish, no other new visual element ships to Dashboard. |
| View Transitions scope | `@view-transition { navigation: auto; }` and the `view-transition-name: flow-wordmark` rule are added **only** inside `dashboard/index.html`'s own `{% block head %}` override — not to `base.html` or the shared `style.css`. This means the transition activates *only* when a page navigates into Dashboard specifically; it does not enable View Transitions for navigation between any other pair of modules (Bank↔Beasiswa, etc.), which stays explicitly out of scope, consistent with the earlier login/company-select spec's stated non-goal of a reusable transition framework. |
| Reduced motion | No custom handling needed — the View Transitions API already respects `prefers-reduced-motion` natively at the browser level (transitions are skipped/shortened automatically); this spec adds no custom CSS keyframes or JS-driven motion that would need separate handling. |

---

## Architecture

### File changes

**Modify `C:\Financehub\app\templates\company_select.html`:**

1. In the existing click handler (the one that already adds the `branch-firing-*` class and delays `requestSubmit` by 180ms), add one line before the `setTimeout` call: if `localStorage.getItem('fh-theme')` is falsy, call `localStorage.setItem('fh-theme', 'dark')`. This must run unconditionally (not gated behind the existing `reduceMotion` early-return), since it's a theme preference, not a motion effect — a reduced-motion user still gets the dark-canvas continuity, they just skip the animated flourish.
2. No other change needed here — `.wordmark` already carries `view-transition-name: flow-wordmark` from the earlier login↔company-select work. The same name is reused for this hop (see point 3); one element can serve as both an outgoing-transition source and an incoming-transition destination across two different navigations, no conflict.

**Modify `C:\Financehub\app\templates\dashboard\index.html`:**

3. Add a `{% block head %}` section (this template doesn't currently define one) containing a small inline `<style>` block, scoped entirely to this one template — not `base.html`, not `static/css/style.css`:
   - `@view-transition { navigation: auto; }`
   - `.navbar-brand { view-transition-name: flow-wordmark; }` — targets the existing navbar link that already wraps both the gradient icon and the "FLOW" text as one unit (there's no separate text-only element to target inside it, so this names the whole link, matching how `.wordmark` on company-select is one named group too).

   View Transitions does not require the outgoing and incoming named elements to be structurally identical — it captures each as an image and interpolates position/size, crossfading the content. Company-select's `.wordmark` group also contains an "Internal" pill that `.navbar-brand` has no equivalent of; that's fine, it simply fades out as part of the crossfade rather than needing a matching counterpart.

**Non-goals:**
- No change to `login.html`'s own `view-transition-name` (it keeps the single `flow-wordmark` name it already has for the login↔company-select hop, untouched).
- No change to any other module template, `base.html`, or `static/css/style.css`.
- No ambient chart, accent-flash, or any new visual element added to Dashboard.
- No change to `/select-company` POST route logic or session handling.

---

## Testing

No backend/logic changes. Existing tests (`test_dashboard_after_company_selection`, `test_company_select_page_has_a_panel_per_company`, etc.) are unaffected — this is pure client-side JS (one `localStorage` call) plus additive CSS (`view-transition-name`, `@view-transition`) that Flask's test client cannot observe and that browsers without View Transitions support simply ignore. Verification is manual/visual:
- Clear `localStorage`, click a company panel, confirm Dashboard loads in dark mode.
- Set a theme manually first (toggle to light), then click a company panel, confirm Dashboard still loads in the user's chosen theme (not forced dark).
- In a View-Transitions-supporting browser (Chrome/Edge), confirm the wordmark visibly glides from its centered position to the navbar rather than popping instantly.
- Confirm no visual/functional change to any other page's navigation (Bank↔Beasiswa, etc. — View Transitions must not activate there).

**Known limitation, confirmed 2026-07-28 (not a bug — accepted as-is):** Chrome does not fire cross-document View Transitions for navigations triggered by a POST form submission, by design (browsers are conservative about animating state-mutating requests). `company_select.html`'s form to `/select-company` is a POST, so the wordmark morph described above never actually plays for this hop — the CSS is correctly in place and harmless, it's just inert given this navigation's own semantics. Confirmed via Chrome 150 with `document.startViewTransition` and cross-document view transitions both supported; the CSS (`view-transition-name: flow-wordmark`) is verified present on the live rendered Dashboard page via `getComputedStyle`. Fixing this for real would mean switching the click handler from native form submission to `fetch()` POST + a separate script-initiated `location.href` navigation — which was deliberately rejected to avoid contradicting this project's "native form, no client-side routing" constraint. The dark-mode-on-first-visit continuity (a plain `localStorage` mechanism, unrelated to View Transitions) is unaffected and works normally.

Sources: [Chrome for Developers — Cross-document view transitions](https://developer.chrome.com/docs/web-platform/view-transitions/cross-document), [CSS-Tricks — Cross-Document View Transitions: The Gotchas Nobody Mentions](https://css-tricks.com/cross-document-view-transitions-part-1/)

## Out of Scope

- Extending View Transitions to any other page pair in the app.
- Any new visual element (chart, accent flash, etc.) on Dashboard.
- Changing Dashboard's default theme behavior for direct navigation (e.g. typing `/dashboard` in the address bar, or navigating there from within the app) — this spec only touches the moment right after company selection.
