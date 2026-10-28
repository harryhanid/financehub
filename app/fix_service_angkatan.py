import re

with open('C:/Financehub/app/modules/beasiswa/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'def get_dashboard_latest_payments(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, limit: int = 20) -> list:',
    'def get_dashboard_latest_payments(company_id: int, years: list = None, pillars: list = None, programs: list = None, jenjangs: list = None, statuses: list = None, angkatans: list = None, limit: int = 20) -> list:'
)

with open('C:/Financehub/app/modules/beasiswa/service.py', 'w', encoding='utf-8') as f:
    f.write(content)
