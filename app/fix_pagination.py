path = r"C:\Financehub\app\templates\sponsorship\data.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

import re

old_pagination = """<a class="budget-btn {% if page <= 1 %}disabled{% endif %}"
         href="?page={{ page - 1 }}{% if filters.cat %}&cat={{ filters.cat|urlencode }}{% endif %}{% if filters.cat3 %}&cat3={{ filters.cat3|urlencode }}{% endif %}{% if filters.description %}&description={{ filters.description|urlencode }}{% endif %}{% if filters.tahun %}&tahun={{ filters.tahun|urlencode }}{% endif %}{% if filters.status %}&status={{ filters.status|urlencode }}{% endif %}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}"
         href="?page={{ page + 1 }}{% if filters.cat %}&cat={{ filters.cat|urlencode }}{% endif %}{% if filters.cat3 %}&cat3={{ filters.cat3|urlencode }}{% endif %}{% if filters.description %}&description={{ filters.description|urlencode }}{% endif %}{% if filters.tahun %}&tahun={{ filters.tahun|urlencode }}{% endif %}{% if filters.status %}&status={{ filters.status|urlencode }}{% endif %}">Next ›</a>"""

new_pagination = """{% set query_str = [] %}
{% for k, v in filters.items() %}
  {% if v is iterable and v is not string %}
    {% for item in v %}
      {% set _ = query_str.append(k ~ '=' ~ item|urlencode) %}
    {% endfor %}
  {% else %}
    {% set _ = query_str.append(k ~ '=' ~ v|urlencode) %}
  {% endif %}
{% endfor %}
{% set filter_qs = ('&' ~ query_str|join('&')) if query_str else '' %}
      <a class="budget-btn {% if page <= 1 %}disabled{% endif %}" href="?page={{ page - 1 }}{{ filter_qs }}">‹ Prev</a>
      <a class="budget-btn {% if page >= total_pages %}disabled{% endif %}" href="?page={{ page + 1 }}{{ filter_qs }}">Next ›</a>"""

c = c.replace(old_pagination, new_pagination)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("Pagination fixed")
