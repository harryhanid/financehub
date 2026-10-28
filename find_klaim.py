import os
for root, dirs, files in os.walk("app/modules"):
    if "klaim" in root.lower() or any("klaim" in f.lower() for f in files):
        print(root)
