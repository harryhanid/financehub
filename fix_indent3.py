with open("app/modules/payment_memo/service.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("                conn.execute(\n            \"\"\"INSERT INTO pam_records", "        conn.execute(\n            \"\"\"INSERT INTO pam_records")

with open("app/modules/payment_memo/service.py", "w", encoding="utf-8") as f:
    f.write(text)
print("Fixed indent in payment_memo/service.py again")
