import os
for root, dirs, files in os.walk("app/modules"):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                content = f.read()
                if "klaim_medical" in content:
                    print(os.path.join(root, file))
