import re
with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

script_match = re.search(r"<script>(.*?)</script>", text, re.DOTALL)
if script_match:
    js = script_match.group(1)
    js = re.sub(r"\{\{.*?\}\}", "'MOCK'", js)
    js = re.sub(r"\{%.*?%\}", "", js)
    with open("test.js", "w", encoding="utf-8") as jsf:
        jsf.write(js)
