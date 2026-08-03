file_path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(file_path, "r", encoding="utf-8") as f:
    html = f.read()

new_script = """{% block scripts %}
<script>
// ─── Date inputs: click/Tab-in opens the native picker, manual typing off ────
// All <input type="date"> on this page (Input-PA form, Edit modal, bulk-date
// bar) should only be settable via the browser's date picker — clicking
// anywhere in the box (not just the calendar icon) opens it immediately, and
// keyboard entry is blocked (Tab/Shift+Tab excepted) so users can't type a
// date by hand. showPicker() is feature-detected once so browsers that don't
// support it (very old only, as of 2026) fall back to normal manual typing
// instead of the field becoming unusable.
(function() {
  var supportsShowPicker = typeof HTMLInputElement.prototype.showPicker === 'function';

  document.addEventListener('click', function (e) {
    if (supportsShowPicker && e.target.matches('input[type="date"]')) {
      e.target.showPicker();
    }
  });
  document.addEventListener('focus', function (e) {
    if (supportsShowPicker && e.target.matches('input[type="date"]')) {
      e.target.showPicker();
    }
  }, true); // capture phase — 'focus' doesn't bubble
  document.addEventListener('keydown', function (e) {
    if (supportsShowPicker && e.target.matches('input[type="date"]') && e.key !== 'Tab') {
      e.preventDefault();
    }
  });
})();
"""

if "supportsShowPicker" not in html:
    html = html.replace("{% block scripts %}\n<script>", new_script)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Script injected successfully.")
else:
    print("Script already injected.")
