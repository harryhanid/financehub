with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re
text = re.sub(
    r'(const \{ td: tdAmt,\s*inp:\s*amtInp \} = tdInput\("number","0",\{min:"0"\}\);)',
    r'const tdKlasifikasi = document.createElement("td"); tdKlasifikasi.style.cssText = "white-space:nowrap;font-size:.8rem;color:var(--text-muted);min-width:110px"; tdKlasifikasi.textContent = "—"; tr._klasCell = tdKlasifikasi;\n  \1',
    text
)
text = re.sub(
    r'\[tdSiswa,tdCat1,tdCat2,tdAmt,tdSisa',
    r'[tdSiswa,tdCat1,tdCat2,tdKlasifikasi,tdAmt,tdSisa',
    text
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
