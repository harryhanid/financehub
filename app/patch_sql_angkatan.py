import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences of {jenjang_sql} followed by anything that isn't angkatan_sql
# Wait, simply replace {jenjang_sql} with {jenjang_sql}{angkatan_sql}
# Because we know angkatan_sql is defined in all those functions!
# But wait, what if it's already there? It's not.
# We also have to be careful with string formatting.

# First, ensure angkatan_sql is in the f-string or string format.
content = content.replace('{jenjang_sql}', '{jenjang_sql}{angkatan_sql}')

# Also we need to make sure the f-strings use it correctly.
# In Python, if we just replace it inside the string literal, it's fine since it's an f-string.
# Wait, some are conn.execute(f"...", ...) or conn.execute("""...""") ?
# Let's check how they are formatted.
# Actually, the python queries are f-strings: f"""..."""
# So just {jenjang_sql}{angkatan_sql} will work.

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)
