import sys

def remove_total():
    with open(r'C:\Financehub\app\modules\sahabat_etf\service.py', 'r', encoding='utf-8') as f:
        content = f.read()

    total_block = """    if years:
        years.append("Total")
        for c in kategori_list:
            c["budget"].append(sum(c["budget"]))
            c["realisasi"].append(sum(c["realisasi"]))
        for p in pillar_list:
            p["budget"].append(sum(p["budget"]))
            p["realisasi"].append(sum(p["realisasi"]))
        """
    
    if total_block in content:
        content = content.replace(total_block, "")
        with open(r'C:\Financehub\app\modules\sahabat_etf\service.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Removed Total")
    else:
        print("Not found")

if __name__ == '__main__':
    remove_total()
