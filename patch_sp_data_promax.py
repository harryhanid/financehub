import sys
import re

def patch_data_html():
    with open(r'C:\Financehub\app\templates\sponsorship\data.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the empty th header
    content = content.replace('<th>CC</th><th>Source</th><th></th>', '<th>CC</th><th>Source</th>')
    
    # Make the row clickable and remove the edit button column
    old_row = """      <tr data-transaksi-id="{{ r.id }}">
        <td>{{ r.id }}</td><td>{{ r.cat }}</td><td>{{ r.description }}</td>
        <td>{{ r.tanggal_form_sponsor }}</td><td>{{ r.tanggal_payment or '' }}</td>
        <td>{{ r.cat1 }}</td><td>{{ r.cat2 }}</td><td>{{ r.cat3 }}</td>
        <td>{{ r.lembaga_perorangan }}</td><td>{{ r.perihal or '' }}</td>
        <td class="num-right">{{ r.amount_request | rupiah(false) }}</td>
        <td class="num-right">{{ r.app_amount | rupiah(false) }}</td><td class="num-right">{{ r.energy_finance_amount | rupiah(false) }}</td>
        <td class="num-right">{{ r.property_amount | rupiah(false) }}</td><td class="num-right">{{ r.agri_amount | rupiah(false) }}</td>
        <td>{{ r.reff or '' }}</td><td>{{ r.status or '' }}</td><td>{{ r.cat4 or '' }}</td>
        <td>{{ r.coa }}</td><td>{{ r.cc_total }}</td><td>{{ r.cc }}</td><td>{{ r.source }}</td>
        <td><button class="budget-btn" onclick="sponsorshipDataEdit({{ r.id }})">Edit</button></td>
      </tr>"""
      
    new_row = """      <tr data-transaksi-id="{{ r.id }}" onclick="sponsorshipDataEdit({{ r.id }})" class="sp-promax-table-row">
        <td>{{ r.id }}</td><td>{{ r.cat }}</td><td>{{ r.description }}</td>
        <td>{{ r.tanggal_form_sponsor }}</td><td>{{ r.tanggal_payment or '' }}</td>
        <td>{{ r.cat1 }}</td><td>{{ r.cat2 }}</td><td>{{ r.cat3 }}</td>
        <td>{{ r.lembaga_perorangan }}</td><td>{{ r.perihal or '' }}</td>
        <td class="num-right">{{ r.amount_request | rupiah(false) }}</td>
        <td class="num-right">{{ r.app_amount | rupiah(false) }}</td><td class="num-right">{{ r.energy_finance_amount | rupiah(false) }}</td>
        <td class="num-right">{{ r.property_amount | rupiah(false) }}</td><td class="num-right">{{ r.agri_amount | rupiah(false) }}</td>
        <td>{{ r.reff or '' }}</td><td>{{ r.status or '' }}</td><td>{{ r.cat4 or '' }}</td>
        <td>{{ r.coa }}</td><td>{{ r.cc_total }}</td><td>{{ r.cc }}</td><td>{{ r.source }}</td>
      </tr>"""
    
    content = content.replace(old_row, new_row)
    
    # Update the modal style and buttons for Promax UI
    old_modal_footer = """      <div class="modal-footer" style="display:flex;gap:.5rem;justify-content:flex-end;padding:.75rem 1rem">
        <button class="btn btn-secondary" onclick="closeModal('sp-edit-modal')">Batal</button>
        <button class="budget-btn" onclick="sponsorshipDataSave()">Simpan</button>
      </div>"""
      
    new_modal_footer = """      <div class="sp-promax-footer" style="margin-top:0; padding:1.25rem 1rem 1rem 1rem; border-top:1px solid var(--border-color); display:flex; justify-content:flex-end; gap:0.75rem; background:var(--bg-card);">
        <button type="button" style="background:transparent; border:1px solid var(--sl-300); color:var(--text-muted); padding:0.6rem 1.5rem; border-radius:8px; font-weight:600; cursor:pointer;" onclick="closeModal('sp-edit-modal')" onmouseover="this.style.background='var(--sl-100)';this.style.color='var(--text-primary)'" onmouseout="this.style.background='transparent';this.style.color='var(--text-muted)'">Batal</button>
        <button type="button" class="sp-promax-submit-btn" style="padding:0.6rem 2rem;" onclick="sponsorshipDataSave()">Simpan Transaksi</button>
      </div>"""
      
    content = content.replace(old_modal_footer, new_modal_footer)

    # Let's also make sure the modal itself has a slightly sleeker appearance
    # It currently uses `<div class="modal">` and `<div class="modal-header">`.
    # Let's wrap the form in a less padded way so the sp-form-card doesn't double-pad
    content = content.replace('<form id="sp-edit-form" class="sp-form-card">', '<form id="sp-edit-form" class="sp-form-card" style="box-shadow:none; border:none; padding:1rem 1.5rem;">')
    
    # We'll inject a little bit of CSS into the block head
    head_injection = """
<style>
.sp-promax-table-row {
  cursor: pointer;
  transition: transform 0.2s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.2s ease, background 0.2s ease;
}
.sp-promax-table-row:hover {
  transform: scale(1.002) translateY(-1px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
  position: relative;
  z-index: 5;
}
[data-theme="dark"] .sp-promax-table-row:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
</style>
"""
    content = content.replace('{% block head %}', '{% block head %}' + head_injection)

    with open(r'C:\Financehub\app\templates\sponsorship\data.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched data.html successfully!")

if __name__ == '__main__':
    patch_data_html()
