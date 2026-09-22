with open('app/templates/payment_memo/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

openEditPamNew = '''  document.getElementById('edit-pam-app-notes').value     = app.notes || '';
  
  const existingContainer = document.getElementById("edit-pam-existing-attachments");
  existingContainer.innerHTML = "";
  document.getElementById("edit-pam-attachment").value = "";
  if (r.attachment_file_id) {
    const ids = r.attachment_file_id.split(',').filter(id => id.trim());
    const keptIds = [...ids];
    ids.forEach(id => {
      const row = document.createElement("div");
      row.style.display = "flex";
      row.style.alignItems = "center";
      row.style.justifyContent = "space-between";
      row.style.background = "#f3f4f6";
      row.style.padding = "2px 6px";
      row.style.borderRadius = "4px";
      
      const link = document.createElement("a");
      link.href = /etf-payment-application/attachment/;
      link.target = "_blank";
      link.style.fontSize = "0.75rem";
      link.style.color = "#2563eb";
      link.textContent = "View File";
      
      const delBtn = document.createElement("button");
      delBtn.textContent = "×";
      delBtn.style.background = "none";
      delBtn.style.border = "none";
      delBtn.style.color = "#dc2626";
      delBtn.style.cursor = "pointer";
      delBtn.style.fontWeight = "bold";
      delBtn.onclick = (e) => {
        e.preventDefault();
        const idx = keptIds.indexOf(id);
        if (idx > -1) keptIds.splice(idx, 1);
        const keptInput = document.getElementById("edit-pam-kept-attachments");
        keptInput.value = keptIds.join(',');
        row.remove();
      };
      
      row.appendChild(link);
      row.appendChild(delBtn);
      existingContainer.appendChild(row);
    });
    document.getElementById("edit-pam-kept-attachments").value = keptIds.join(',');
  } else {
    document.getElementById("edit-pam-kept-attachments").value = "";
  }
  
  openModal('modal-edit-pam');'''

content = content.replace("  document.getElementById('edit-pam-app-notes').value     = app.notes || '';\n  openModal('modal-edit-pam');", openEditPamNew)

submitEditPamOld = '''    pam: {
      pam_no:          document.getElementById('edit-pam-no').value.trim() || null,
      keterangan:      document.getElementById('edit-pam-keterangan').value.trim(),
      requestors_name: document.getElementById('edit-pam-requestor').value.trim(),
      dpp:             parseFloat(document.getElementById('edit-pam-dpp').value.replace(/,/g, '')) || null,
      ppn:             parseFloat(document.getElementById('edit-pam-ppn').value.replace(/,/g, '')) || null,
      others:          parseFloat(document.getElementById('edit-pam-others').value.replace(/,/g, '')) || null,
      total_amount:    parseFloat(document.getElementById('edit-pam-amount').value.replace(/,/g, '')) || null,
      pam_date:        document.getElementById('edit-pam-date').value || null,
      due_date:        document.getElementById('edit-pam-due').value || null,
      tanggal_bayar:   document.getElementById('edit-pam-tanggal-bayar').value || null,
      pt:              document.getElementById('edit-pam-pt').value || null,
      cost_center:     document.getElementById('edit-pam-cost-center').value || null,
    },
    app: {
      notes: document.getElementById('edit-pam-app-notes').value.trim()
    }
  };
  const res = await apiFetch(/payment-memo/pam//edit, {
    method: 'POST', body: JSON.stringify(payload)
  });'''

submitEditPamNew = '''    pam: {
      pam_no:          document.getElementById('edit-pam-no').value.trim() || null,
      keterangan:      document.getElementById('edit-pam-keterangan').value.trim(),
      requestors_name: document.getElementById('edit-pam-requestor').value.trim(),
      dpp:             parseFloat(document.getElementById('edit-pam-dpp').value.replace(/,/g, '')) || null,
      ppn:             parseFloat(document.getElementById('edit-pam-ppn').value.replace(/,/g, '')) || null,
      others:          parseFloat(document.getElementById('edit-pam-others').value.replace(/,/g, '')) || null,
      total_amount:    parseFloat(document.getElementById('edit-pam-amount').value.replace(/,/g, '')) || null,
      pam_date:        document.getElementById('edit-pam-date').value || null,
      due_date:        document.getElementById('edit-pam-due').value || null,
      tanggal_bayar:   document.getElementById('edit-pam-tanggal-bayar').value || null,
      pt:              document.getElementById('edit-pam-pt').value || null,
      cost_center:     document.getElementById('edit-pam-cost-center').value || null,
      attachment_file_id: document.getElementById("edit-pam-kept-attachments").value,
    },
    app: {
      notes: document.getElementById('edit-pam-app-notes').value.trim()
    }
  };
  
  const fd = new FormData();
  fd.append("data", JSON.stringify(payload));
  const fileInput = document.getElementById("edit-pam-attachment");
  if (fileInput && fileInput.files) {
    for (let i = 0; i < fileInput.files.length; i++) {
      fd.append("files", fileInput.files[i]);
    }
  }
  
  const res = await apiFetch(/payment-memo/pam//edit, {
    method: 'POST', body: fd
  });'''

content = content.replace(submitEditPamOld, submitEditPamNew)

with open('app/templates/payment_memo/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

