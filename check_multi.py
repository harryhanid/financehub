with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()
import re
print("Occurrences of new_end snippet:", len(re.findall(r'# Update PA status to on_process and set nomor_pam', text)))
