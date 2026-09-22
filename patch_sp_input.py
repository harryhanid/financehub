import sys
import re

def rewrite():
    with open(r'C:\Financehub\app\templates\sponsorship\input.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We will replace the entire <form id="sp-input-form" class="sp-form-card"> block.
    # The form ends at </form>
    
    new_form = """  <form id="sp-input-form" class="sp-form-card">
    <div class="sp-form-section-title">Form Header (Berlaku untuk semua baris)</div>
    <div class="sp-form-grid">
      <div class="sp-form-field">
        <label>Cat</label>
        <select id="sp-in-cat">{% for c in cat_choices %}<option value="{{ c }}">{{ c }}</option>{% endfor %}</select>
      </div>
      <div class="sp-form-field">
        <label>Description</label>
        <select id="sp-in-description">{% for d in description_choices %}<option value="{{ d }}">{{ d }}</option>{% endfor %}</select>
      </div>
    </div>

    <div class="sp-form-section-title sp-form-section-title-divider">Detail &amp; Tanggal (Berlaku untuk semua baris)</div>
    <div class="sp-form-grid">
      <div class="sp-form-field sp-form-span2">
        <label>Lembaga/Perorangan</label>
        <input type="text" id="sp-in-lembaga" list="sp-lembaga-datalist" autocomplete="off">
        <datalist id="sp-lembaga-datalist"></datalist>
      </div>
      <div class="sp-form-field">
        <label>Tanggal Form Sponsor</label>
        <input type="date" id="sp-in-tanggal-form">
      </div>
      <div class="sp-form-field">
        <label>Tanggal Payment</label>
        <input type="date" id="sp-in-tanggal-payment">
      </div>
      <div class="sp-form-field sp-form-span2">
        <label>Perihal</label>
        <input type="text" id="sp-in-perihal">
      </div>
      <div class="sp-form-field">
        <label>Reff</label>
        <input type="text" id="sp-in-reff">
      </div>
      <div class="sp-form-field">
        <label>Status</label>
        <input type="text" id="sp-in-status">
      </div>
    </div>

    <details class="sp-form-advanced">
      <summary>Lanjutan (COA, CC Total, CC, Source)</summary>
      <div class="sp-form-grid">
        <div class="sp-form-field sp-form-span2">
          <label>COA</label>
          <input type="text" id="sp-in-coa" value="701078002">
        </div>
        <div class="sp-form-field sp-form-span2">
          <label>CC Total</label>
          <input type="text" id="sp-in-cc-total" value="SMT - Corporate Communication">
        </div>
        <div class="sp-form-field sp-form-span2">
          <label>CC</label>
          <input type="text" id="sp-in-cc" value="POSPON">
        </div>
        <div class="sp-form-field sp-form-span2">
          <label>Source</label>
          <input type="text" id="sp-in-source" value="Sponsor">
        </div>
      </div>
    </details>

    <div class="sp-form-section-title sp-form-section-title-divider">Transaksi (Lines)</div>
    <div id="sp-lines-container">
      <!-- Lines injected by JS -->
    </div>
    
    <div style="margin-top:1rem;">
      <button type="button" class="btn btn-secondary btn-sm" onclick="sponsorshipAddLine()">+ Tambah Transaksi</button>
    </div>
  </form>"""

    # Replace everything from <form id="sp-input-form" class="sp-form-card"> to </form>
    pattern = r'<form id="sp-input-form" class="sp-form-card">.*?</form>'
    new_content = re.sub(pattern, new_form, content, flags=re.DOTALL)
    
    with open(r'C:\Financehub\app\templates\sponsorship\input.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("Patched input.html successfully!")

if __name__ == '__main__':
    rewrite()
