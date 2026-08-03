path = r"C:\Financehub\app\templates\sponsorship\dashboard.html"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

c = c.replace(
    '''<select class="sp-dash-filter" data-param="tahun"><option value="">Semua Tahun</option>
      {% for y in years %}<option value="{{ y }}">{{ y }}</option>{% endfor %}
    </select>''',
    '''<select class="sp-dash-filter" data-param="tahun">
      <option value="">Semua Tahun</option>
      {% for y in years %}<option value="{{ y }}" {% if y == '2026' %}selected{% endif %}>{{ y }}</option>{% endfor %}
    </select>'''
)

with open(path, "w", encoding="utf-8") as f:
    f.write(c)

print("done dashboard.html")
