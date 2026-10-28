with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
old_budget_set = """        if (budgetEl) {
          budgetEl.textContent = sisa !== null ? "Rp " + sisa.toLocaleString("id-ID") : "-";
        }"""
new_budget_set = """        if (budgetEl) {
          budgetEl.textContent = sisa !== null ? "Rp " + sisa.toLocaleString("id-ID") : "-";
        }
        tr._sisaBudget = sisa;"""

if old_budget_set in text:
    text = text.replace(old_budget_set, new_budget_set)
    with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
        f.write(text)
    print("Added tr._sisaBudget = sisa;")
else:
    print("Could not find old_budget_set")
