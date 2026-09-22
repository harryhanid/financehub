import sys

def patch():
    with open(r'C:\Financehub\app\templates\beasiswa\index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.replace('div.addEventListener("mousedown", () => bgtSelectSiswa(s.code, s.nama));', 'div.addEventListener("click", () => bgtSelectSiswa(s.code, s.nama));')
    content = content.replace('div.addEventListener("mousedown", () => bgtCat2Select(c));', 'div.addEventListener("click", () => bgtCat2Select(c));')
    content = content.replace('d.addEventListener("mousedown", () => { hid.value=c; lbl.textContent=c; lbl.style.color="var(--sl-700)"; pan.style.display="none"; si.value=""; });', 'd.addEventListener("click", () => { hid.value=c; lbl.textContent=c; lbl.style.color="var(--sl-700)"; pan.style.display="none"; si.value=""; });')
    content = content.replace('div.addEventListener("mousedown", () => lprSelectSiswa(s.code, s.nama));', 'div.addEventListener("click", () => lprSelectSiswa(s.code, s.nama));')

    with open(r'C:\Financehub\app\templates\beasiswa\index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == '__main__':
    patch()
