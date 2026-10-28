import os
for root, dirs, files in os.walk("app"):
    for file in files:
        if file.endswith(".py"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                content = f.read()
                if "sys.exit(1)" in content or "os._exit(1)" in content:
                    print(os.path.join(root, file))
