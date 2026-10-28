import re

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# For api_dashboard_summary, api_dashboard_breakdown, api_dashboard_monthly, api_dashboard_latest_payments, api_dashboard_program_summary, api_dashboard_pillar_yearly
endpoints = ['api_dashboard_summary', 'api_dashboard_breakdown', 'api_dashboard_monthly', 'api_dashboard_latest_payments', 'api_dashboard_program_summary', 'api_dashboard_pillar_yearly']

for ep in endpoints:
    # Find the function body, inject angkatans parsing
    # The existing code has:
    # jenjangs_str = request.args.get("jenjangs", "")
    # jenjangs = [j for j in jenjangs_str.split(",") if j]
    
    # We'll replace the jenjangs logic to also include angkatans
    replacement = '''jenjangs_str = request.args.get("jenjangs", "")
    jenjangs = [j for j in jenjangs_str.split(",") if j]
    angkatans_str = request.args.get("angkatans", "")
    angkatans = [a for a in angkatans_str.split(",") if a]'''
    content = re.sub(fr'jenjangs_str = request\.args\.get\("jenjangs", ""\).*?jenjangs = \[j for j in jenjangs_str\.split\(\",\"\) if j\]', replacement, content, flags=re.DOTALL)
    
    # Also we need to add angkatans to the service call
    # e.g., get_dashboard_summary(_cid(), years, pillars, programs, jenjangs, statuses)
    # -> get_dashboard_summary(_cid(), years, pillars, programs, jenjangs, statuses, angkatans)
    content = re.sub(
        r'(get_dashboard_[a-z_]+)\(_cid\(\), (.*?)(?:, statuses)?, statuses\)',
        r'\1(_cid(), \2, statuses, angkatans)',
        content
    )
    # Wait, the regex above might be brittle. Let's just do:
    content = content.replace('jenjangs, statuses)', 'jenjangs, statuses, angkatans)')

with open('C:/Financehub/app/modules/beasiswa/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
