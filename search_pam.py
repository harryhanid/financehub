import os
for root, dirs, files in os.walk("app"):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                lines = f.readlines()
                for i, line in enumerate(lines):
                    if "def update" in line and "pam" in line.lower():
                        print(f"{os.path.join(root, file)}:{i+1}: {line.strip()}")
                    elif "route" in line and "pam" in line.lower() and "update" in line.lower():
                        print(f"{os.path.join(root, file)}:{i+1}: {line.strip()}")
