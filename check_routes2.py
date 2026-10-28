import os
import re

for root, dirs, files in os.walk("app/modules/payment_memo"):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                content = f.read()
                for line in content.splitlines():
                    if "@bp.route" in line:
                        print(f"{file}: {line}")
