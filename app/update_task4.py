path = r"C:\Financehub\app\templates\etf_payment_application\index.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
"""{% extends "base.html" %}
{% block title %}Payment Application{% endblock %}""",
"""{% extends "base.html" %}
{% set full_bleed = active_tab != 'input' %}
{% block title %}Payment Application{% endblock %}"""
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("task 4 done")
