import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    '''@bp.route("/approval-budget", methods=["GET"])
@etf_company_required''',
    '''@bp.route("/approval-budget", methods=["GET"])
@jwt_html_required
@etf_company_required'''
)

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
