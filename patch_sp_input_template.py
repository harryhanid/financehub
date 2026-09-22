import sys

def rewrite():
    with open(r'C:\Financehub\app\templates\sponsorship\input.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    template_html = """    <!-- Lines injected by JS -->
    <template id="sp-line-template">
      <div class="sp-line-row" style="position:relative; border:1px solid #e5e7eb; padding:1rem; border-radius:.375rem; margin-bottom:1rem; background:#f9fafb;">
        <button type="button" class="btn btn-sm" style="position:absolute; top:1rem; right:1rem; padding:0.25rem 0.5rem; background:#ef4444; color:#fff;" onclick="this.closest('.sp-line-row').remove()">X</button>
        <div class="sp-form-grid">
          <div class="sp-form-field sp-form-span2">
            <label>Cat1 (Perusahaan)</label>
            <input type="text" class="sp-line-cat1-search" placeholder="Cari perusahaan...">
            <input type="hidden" class="sp-line-cat1">
            <div class="sp-autocomplete-results sp-line-cat1-results"></div>
          </div>
          <div class="sp-form-field">
            <label>Cat2</label>
            <input type="text" class="sp-line-cat2" readonly>
          </div>
          <div class="sp-form-field">
            <label>Cat3 (Pillar)</label>
            <input type="text" class="sp-line-cat3" readonly>
          </div>
          <div class="sp-form-field">
            <label>Cat4</label>
            <select class="sp-line-cat4"><option value="">(blank)</option>{% for c in cat4_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
          </div>
          <div class="sp-form-field">
            <label>Amount Request</label>
            <input type="text" class="sp-line-amount" placeholder="0">
          </div>
        </div>
      </div>
    </template>"""

    content = content.replace('<!-- Lines injected by JS -->', template_html)
    
    with open(r'C:\Financehub\app\templates\sponsorship\input.html', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Patched template successfully!")

if __name__ == '__main__':
    rewrite()
