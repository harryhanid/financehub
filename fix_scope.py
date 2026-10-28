with open("app/templates/payment_memo/index.html", "r", encoding="utf-8") as f:
    text = f.read()

import re

# In ipayAddRow (around line 5258)
text = re.sub(
    r'const hidEtfLineId = document\.createElement\("input"\); hidEtfLineId\.type="hidden"; hidEtfLineId\.value=""; tr\._hidEtfLineId=hidEtfLineId; tdSiswa\.appendChild\(hidEtfLineId\);',
    r'const hidEtfLineId_1 = document.createElement("input"); hidEtfLineId_1.type="hidden"; hidEtfLineId_1.value=""; tr._hidEtfLineId=hidEtfLineId_1; tdSiswa.appendChild(hidEtfLineId_1);',
    text
)

# In klaimAddSiswa (around line 5632)
text = re.sub(
    r'const hidEtfLineId = document\.createElement\("input"\); hidEtfLineId\.type = "hidden"; hidEtfLineId\.className = "klaim-line-id"; tr\._hidEtfLineId = hidEtfLineId;\s*tdSiswa\.appendChild\(hidEtfLineId\);',
    r'const hidEtfLineId_2 = document.createElement("input"); hidEtfLineId_2.type = "hidden"; hidEtfLineId_2.className = "klaim-line-id"; tr._hidEtfLineId = hidEtfLineId_2;\n  tdSiswa.appendChild(hidEtfLineId_2);',
    text
)

# In klaimAddCat2Row (around line 5721)
text = re.sub(
    r'const hidEtfLineId = document\.createElement\("input"\); hidEtfLineId\.type = "hidden"; hidEtfLineId\.className = "klaim-line-id"; tr\._hidEtfLineId = hidEtfLineId;\s*tdLabel\.appendChild\(hidEtfLineId\);',
    r'const hidEtfLineId_3 = document.createElement("input"); hidEtfLineId_3.type = "hidden"; hidEtfLineId_3.className = "klaim-line-id"; tr._hidEtfLineId = hidEtfLineId_3;\n  tdLabel.appendChild(hidEtfLineId_3);',
    text
)

with open("app/templates/payment_memo/index.html", "w", encoding="utf-8") as f:
    f.write(text)
print("Renamed variables to prevent scope collisions")
