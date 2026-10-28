with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()
if "hidEtfLineId =" in text or "const hidEtfLineId" in text:
    print("WARNING: Unreplaced instances found!")
else:
    print("All good!")
