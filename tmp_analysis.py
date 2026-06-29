import sys
sys.stdout.reconfigure(encoding='utf-8')
import csv
from collections import defaultdict

rows = []
with open(r'C:\Users\25010160\Downloads\Cleaned Data - combined_data.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        rows.append(row)

def parse_idr(s):
    if not s or s in ('0','','NULL','#N/A'): return 0.0
    s = s.replace('Rp','').replace(',','').replace(' ','').strip()
    try: return float(s)
    except: return 0.0

def parse_pct(s):
    s = s.strip().replace('%','')
    try: return float(s)
    except: return 0.0

def parse_int(s):
    try: return int(float(s))
    except: return 0

for r in rows:
    r['_gp']         = parse_idr(r['Gross_Profit'])
    r['_net']        = parse_idr(r['Net_Sales'])
    r['_sales']      = parse_idr(r['Total_Sales'])
    r['_disc_pct']   = parse_pct(r['discount_%'])
    r['_returned']   = parse_int(r['returned'])
    r['_qty']        = parse_int(r['quantity'])
    r['_cost_u']     = parse_idr(r['cost_price'])
    r['_list_u']     = parse_idr(r['list_price'])
    r['_below_cost'] = 1 if r['_cost_u'] > r['_list_u'] and r['_list_u'] > 0 else 0
    if r['_below_cost']:
        r['_unit_loss'] = (r['_cost_u'] - r['_list_u']) * r['_qty']
    else:
        r['_unit_loss'] = 0

total        = len(rows)
total_net    = sum(r['_net'] for r in rows)
total_gp_net = sum(r['_gp'] for r in rows)
gp_margin_base = 100 * total_gp_net / total_net if total_net > 0 else 0

print('='*60)
print('WHAT-IF SCENARIO CALCULATIONS')
print('='*60)
print(f'Baseline  Total Net Sales:    Rp{total_net:,.0f}')
print(f'Baseline  Total Gross Profit: Rp{total_gp_net:,.0f}')
print(f'Baseline  GP Margin:          {gp_margin_base:.1f}%')
print()

# SCENARIO A
print('SCENARIO A: Remove all below-cost SKU sales')
below = [r for r in rows if r['_below_cost'] == 1]
above = [r for r in rows if r['_below_cost'] == 0]
unit_loss_total = sum(r['_unit_loss'] for r in below)
gp_below  = sum(r['_gp'] for r in below)
gp_above  = sum(r['_gp'] for r in above)
net_below = sum(r['_net'] for r in below)
net_above = sum(r['_net'] for r in above)
new_margin_a = 100 * gp_above / net_above if net_above > 0 else 0
print(f'  Below-cost transactions:        {len(below):,}  ({100*len(below)/total:.1f}%)')
print(f'  Revenue that would be lost:     Rp{net_below:,.0f}')
print(f'  GP currently from below-cost:   Rp{gp_below:,.0f}')
print(f'  Unit-level loss (cost>price):   Rp{unit_loss_total:,.0f}  = IDR {unit_loss_total/1e9:.2f}B')
print(f'  New GP after removal:           Rp{gp_above:,.0f}')
print(f'  New GP margin:                  {new_margin_a:.1f}%  (was {gp_margin_base:.1f}%)')
print()

# SCENARIO B
print('SCENARIO B: Cap discounts at 10%  (convert 20% and 30% to 10%)')
n_20    = sum(1 for r in rows if r['_disc_pct'] == 20)
n_30    = sum(1 for r in rows if r['_disc_pct'] == 30)
gp_20   = sum(r['_gp'] for r in rows if r['_disc_pct'] == 20)
gp_30   = sum(r['_gp'] for r in rows if r['_disc_pct'] == 30)
sales_20 = sum(r['_sales'] for r in rows if r['_disc_pct'] == 20)
sales_30 = sum(r['_sales'] for r in rows if r['_disc_pct'] == 30)
# At 10% disc: net = full_price * 0.90  (currently at 20%: net = full_price * 0.80)
sim_net_20 = sales_20 * 0.90
sim_net_30 = sales_30 * 0.90
sim_gp_20  = sim_net_20 * 0.809
sim_gp_30  = sim_net_30 * 0.809
gain_b     = (sim_gp_20 + sim_gp_30) - (gp_20 + gp_30)
print(f'  20%-disc txns: {n_20:,} | GP now: Rp{gp_20:,.0f}  -> if 10%: Rp{sim_gp_20:,.0f}')
print(f'  30%-disc txns: {n_30:,} | GP now: Rp{gp_30:,.0f}  -> if 10%: Rp{sim_gp_30:,.0f}')
print(f'  GP GAIN from capping discounts: Rp{gain_b:,.0f}  = IDR {gain_b/1e9:.2f}B')
print(f'  Transactions affected:          {n_20+n_30:,}  ({100*(n_20+n_30)/total:.1f}% of all txns)')
print()

# SCENARIO C
print('SCENARIO C: Improve Medan productivity to Surabaya level')
medan  = [r for r in rows if r['store_name'] == 'Medan Center']
sbya   = [r for r in rows if r['store_name'] == 'Surabaya Outlet']
jakarta= [r for r in rows if r['store_name'] == 'Jakarta Flagship']
net_medan = sum(r['_net'] for r in medan)
net_sbya  = sum(r['_net'] for r in sbya)
net_jkt   = sum(r['_net'] for r in jakarta)
gp_sbya   = sum(r['_gp'] for r in sbya)
gp_medan  = sum(r['_gp'] for r in medan)
rpm_sbya  = net_sbya / 336
rpm_jkt   = net_jkt / 179
rpm_medan = net_medan / 728
target_sbya = rpm_sbya * 728
target_jkt  = rpm_jkt * 728
gain_c_sbya = target_sbya - net_medan
gain_c_jkt  = target_jkt  - net_medan
gp_ratio_sbya = gp_sbya / net_sbya if net_sbya > 0 else 0
gain_gp_c = gain_c_sbya * gp_ratio_sbya
print(f'  Medan current:   Rp{rpm_medan:,.0f}/m2  ({net_medan/1e9:.2f}B total)')
print(f'  Surabaya bench:  Rp{rpm_sbya:,.0f}/m2  ({net_sbya/1e9:.2f}B total)')
print(f'  Jakarta bench:   Rp{rpm_jkt:,.0f}/m2  ({net_jkt/1e9:.2f}B total)')
print(f'  If Medan reaches Surabaya level:')
print(f'    Revenue gain:  Rp{gain_c_sbya:,.0f}  = IDR {gain_c_sbya/1e9:.2f}B')
print(f'    GP gain (est): Rp{gain_gp_c:,.0f}  = IDR {gain_gp_c/1e9:.2f}B')
print(f'  If Medan reaches Jakarta level:')
print(f'    Revenue gain:  Rp{gain_c_jkt:,.0f}  = IDR {gain_c_jkt/1e9:.2f}B')
print()

print('='*60)
print('SUMMARY COMPARISON  (5-year basis)')
print('='*60)
print(f'  Scenario A  Remove below-cost SKUs:   IDR {abs(unit_loss_total)/1e9:.2f}B GP recovery')
print(f'  Scenario B  Cap discounts at 10%:      IDR {gain_b/1e9:.2f}B GP gain')
print(f'  Scenario C  Fix Medan (->Surabaya):    IDR {gain_c_sbya/1e9:.2f}B revenue  |  IDR {gain_gp_c/1e9:.2f}B GP gain')
print()

# ─────────────────────────────────────
# RISK SCORE
# ─────────────────────────────────────
print('='*60)
print('RISK SCORE: "Transaction Loss Risk"  (0-100)')
print('='*60)
print()
print('  Formula factors (based on discovered patterns):')
print('    Base score = 0')
print('    +40  if below-cost SKU (cost_price > list_price)')
print('    +20  if discount >= 20%  (GP margin drops below 73%)')
print('    +10  if discount = 10%   (moderate margin erosion)')
print('    +15  if store = Medan Center  (highest return + lowest productivity)')
print('    +15  if category = Accessories  (highest return rate 10.38%)')
print('    +10  if month in {2,5,8,10}  (peak return months)')
print('    Cap at 100')
print()

# Validate: high-risk score group should have higher actual loss indicators
buckets = defaultdict(lambda: {'n':0,'ret':0,'below':0,'gp':0})
for r in rows:
    score = 0
    if r['_below_cost']:            score += 40
    if r['_disc_pct'] >= 20:        score += 20
    elif r['_disc_pct'] == 10:      score += 10
    if r['store_name'] == 'Medan Center': score += 15
    if r['category'] == 'Accessories':   score += 15
    try:
        m = int(r['date'].split('-')[1])
        if m in {2,5,8,10}:         score += 10
    except: pass
    score = min(score, 100)
    if score >= 60:   bucket = 'HIGH (>=60)'
    elif score >= 30: bucket = 'MED  (30-59)'
    else:             bucket = 'LOW  (<30)'
    buckets[bucket]['n']     += 1
    buckets[bucket]['ret']   += r['_returned']
    buckets[bucket]['below'] += r['_below_cost']
    buckets[bucket]['gp']    += r['_gp']

print('  Validation — risk score vs actual outcomes:')
print(f'  {"Group":<15} {"Txns":>7} {"Return%":>9} {"Below-cost%":>12} {"Total GP":>20}')
for k in ['HIGH (>=60)', 'MED  (30-59)', 'LOW  (<30)']:
    v = buckets[k]
    if v['n'] == 0: continue
    ret_rate   = 100 * v['ret'] / v['n']
    below_rate = 100 * v['below'] / v['n']
    print(f'  {k:<15} {v["n"]:>7,} {ret_rate:>8.1f}% {below_rate:>11.1f}% {v["gp"]:>20,.0f}')

print()
print('  Excel formula (Column references: G=discount_%, H=returned, I=category,')
print('                 J=store_name, K=cost_price, L=list_price, B=date)')
print()
print('  =MIN(100,')
print('    IF(K2>L2,40,0)')
print('   +IF(G2="20%",20,IF(G2="30%",20,IF(G2="10%",10,0)))')
print('   +IF(J2="Medan Center",15,0)')
print('   +IF(I2="Accessories",15,0)')
print('   +IF(OR(MONTH(B2)=2,MONTH(B2)=5,MONTH(B2)=8,MONTH(B2)=10),10,0)')
print('  )')
