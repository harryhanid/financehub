import openpyxl
import io
import datetime

wb = openpyxl.load_workbook('C:\\Financehub\\Sponsorship - MASTER.xlsx', data_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
print("Row 1 (Header):", rows[0])
if len(rows) > 1:
    print("Row 2 (Data):", rows[1])
    print("Type of Tanggal Form:", type(rows[1][3]))
