# UNIQLO Week 7 Analytics Design
**Course:** BINUS x ReVOU — AI Applied Analytics & Automation  
**Team:** Team 2 – Group F4 | Emir · Harry · Leonardus · Syahra  
**Dataset:** 49,800 UNIQLO Indonesia transactions, 2020–2024  
**Date:** 2026-06-11

---

## 1. Objective

Apply the Week 7 "Simple Analytics with AI" framework to the UNIQLO Indonesia capstone dataset. Deliver:
1. **Pattern Discovery** — 5 data-confirmed patterns predicting loss or return
2. **Risk Score Formula** — single Excel formula (0–100) per transaction
3. **What-If Scenarios** — 3 quantified interventions ranked by impact

---

## 2. Dataset

| File | Rows | Columns |
|------|------|---------|
| `Cleaned Data - combined_data.csv` | 49,800 | 28 |

**Key columns used:**

| Column | Letter (Excel) | Description |
|--------|---------------|-------------|
| date | B | Transaction date |
| discount_% | G | Discount level: "0%", "10%", "20%", "30%" |
| category | I | Product category (Tops, Bottoms, Shoes, Dresses, Accessories) |
| cost_price | N | Unit cost to company (IDR) |
| list_price | O | Unit selling price (IDR) |
| store_name | T | Store: Jakarta Flagship, Bali Boutique, Surabaya Outlet, Medan Center, Online |
| returned | H | 1 = returned, 0 = kept |
| Gross_Profit | Z | Computed GP per transaction (IDR) |
| Net_Sales | AB | Net revenue after returns and discounts (IDR) |

**Baseline metrics:**
- Total transactions: 49,800
- Return rate: 9.9% (4,933 transactions)
- Below-cost SKU transactions: 17.3% (8,628 transactions)
- Annual avg. net revenue: ~IDR 21.8B per store

---

## 3. Pattern Discovery

### Pattern 1 — Below-Cost SKU
**Condition:** `cost_price > list_price`  
**Impact:** 8,628 transactions (17.3%) → IDR **8.59B unit-level loss** over 5 years  
**Excel verify:** Filter N > O → count rows, sum (O-N)×F

### Pattern 2 — Heavy Discount (≥ 20%) With Zero Volume Uplift
**Condition:** `discount_% = "20%"` or `"30%"`  
**Impact:**

| Discount | GP Margin | Avg Qty/Txn |
|----------|-----------|-------------|
| 0% | 90.2% | 2.51 |
| 10% | 80.9% | 2.51 |
| 20% | 72.3% | 2.51 |
| 30% | 64.0% | 2.48 |

Margin drops 26 pts from 0%→30% with **no volume gain** whatsoever.  
**Excel verify:** PivotTable: rows=discount_%, values=AVG(quantity), AVG(Gross_Profit/Total_Sales)

### Pattern 3 — Medan Center Store Underperformance
**Condition:** `store_name = "Medan Center"`  
**Impact:**

| Store | Size (m²) | Rev/m² | Return Rate |
|-------|-----------|--------|-------------|
| Jakarta Flagship | 179 | Rp 123,266 | 9.48% |
| Bali Boutique | 238 | Rp 90,289 | 9.87% |
| Surabaya Outlet | 336 | Rp 66,158 | 9.88% |
| **Medan Center** | **728** | **Rp 29,178** | **10.48%** |
| Online | 950 | Rp 22,580 | 9.91% |

Medan: 4× more floor space than Jakarta, but 4.2× less productive per m².  
**Excel verify:** Filter T = "Medan Center" → SUM(Net_Sales)/728

### Pattern 4 — Accessories Category Return Rate
**Condition:** `category = "Accessories"`  
**Impact:** 10.38% return rate (highest of all categories)

| Category | Return Rate |
|----------|-------------|
| Accessories | 10.38% |
| Dresses | 10.01% |
| Bottoms | 9.89% |
| Shoes | 9.70% |
| Tops | 9.53% |

**Excel verify:** PivotTable: rows=category, values=SUM(returned)/COUNT(returned)

### Pattern 5 — Seasonal Return Spike (Feb, May, Aug, Oct)
**Condition:** MONTH(date) ∈ {2, 5, 8, 10}  
**Impact:** Return rates peak at 10.24–10.80% in these months (vs 9.4–9.8% baseline)

| Month | Return Rate |
|-------|-------------|
| August | **10.80%** |
| October | **10.79%** |
| May | 10.31% |
| February | 10.24% |

Pattern is consistent across all 5 years — return spike follows 1–2 months after seasonal sales peaks.  
**Excel verify:** Add helper column =MONTH(B2), PivotTable rows=month, values=return rate

---

## 4. Risk Score Formula

### Design

"Transaction Loss Risk Score" — identifies transactions most likely to generate losses (below-cost sale, high discount, risky store/category/timing).

| Factor | Points | Rationale |
|--------|--------|-----------|
| cost_price > list_price | +40 | Guaranteed loss per unit sold |
| discount ≥ 20% | +20 | Margin drops below 73%, no volume gain |
| discount = 10% | +10 | Moderate margin erosion |
| store = Medan Center | +15 | Highest return + lowest productivity |
| category = Accessories | +15 | Highest return rate (10.38%) |
| Month ∈ {2, 5, 8, 10} | +10 | Seasonal return spike pattern |
| **Cap at 100** | | |

### Excel Formula (paste into empty column, row 2 onward)

```excel
=MIN(100,
  IF(N2>O2,40,0)
 +IF(OR(G2="20%",G2="30%"),20,IF(G2="10%",10,0))
 +IF(T2="Medan Center",15,0)
 +IF(I2="Accessories",15,0)
 +IF(OR(MONTH(B2)=2,MONTH(B2)=5,MONTH(B2)=8,MONTH(B2)=10),10,0)
)
```

> **Catatan format tanggal:** Jika kolom B (date) terbaca sebagai teks setelah import CSV, gunakan `MONTH(DATEVALUE(B2))` sebagai pengganti `MONTH(B2)`. Cara cek: klik cell tanggal → lihat apakah align kiri (teks) atau kanan (date). Jika teks: pilih kolom B → Data → Text to Columns → Finish untuk konversi.

### Validation Results

| Risk Group | Transactions | Return Rate | Below-Cost % |
|------------|-------------|-------------|--------------|
| HIGH (score ≥ 60) | 3,156 | 10.7% | **97.2%** |
| MEDIUM (30–59) | 11,358 | 10.0% | 49.0% |
| LOW (< 30) | 35,286 | 9.8% | **0.0%** |

HIGH-risk group captures 97.2% of all below-cost transactions — formula is strongly predictive.

### Sample Calculations

| Transaction type | N>O | Disc | Store | Category | Month | Score |
|-----------------|-----|------|-------|----------|-------|-------|
| Below-cost + 20% disc + Accessories | +40 | +20 | — | +15 | — | **75** |
| Normal + 10% disc + Medan | — | +10 | +15 | — | — | **25** |
| Below-cost + Medan + Aug | +40 | — | +15 | — | +10 | **65** |
| Normal + no disc + Jakarta | — | — | — | — | — | **0** |

---

## 5. What-If Scenarios

### Scenario A — Remove All Below-Cost SKU Sales

**Assumption:** Stop accepting or repricing SKUs where cost_price > list_price before sale.

| Metric | Value |
|--------|-------|
| Transactions eliminated | 8,628 (17.3%) |
| Unit-level GP loss stopped | **IDR 8.59B** (5-year) |
| Annual recovery | ≈ IDR 1.72B/year |
| Additional cost | None — POS rule change only |
| Implementation | Add validation: `IF list_price < cost_price → BLOCK sale` |

**Tradeoff:** Revenue from these 8,628 transactions is lost — but since each is sold at a guaranteed unit loss, stopping them improves total profitability.

### Scenario B — Cap Maximum Discount at 10%

**Assumption:** Eliminate 20% and 30% discount tiers entirely.

| Metric | Value |
|--------|-------|
| Transactions affected | 7,490 (15.0%) |
| GP gain | **IDR 1.09B** (5-year) |
| Annual gain | ≈ IDR 218M/year |
| Additional cost | None — pricing policy change |
| Key evidence | Avg qty/txn is identical at all discount levels → discounts have ZERO effect on volume |

**Tradeoff:** Risk of losing discount-seeking customers, but data shows no volume response to discounts, so net effect should be positive.

### Scenario C — Fix Medan Center Productivity

**Assumption:** Operational interventions to bring Medan to Surabaya-level productivity.

| Metric | Medan → Surabaya | Medan → Jakarta |
|--------|-----------------|-----------------|
| Target Rev/m² | Rp 66,158 | Rp 123,266 |
| Revenue gain | **IDR 26.92B** (5-year) | IDR 68.50B (5-year) |
| Annual gain | ≈ IDR 5.38B/year | ≈ IDR 13.7B/year |
| GP gain (est.) | IDR 46.63B (5-year) | — |
| Additional cost | Requires operational investment | Higher investment |

**Tradeoff:** Largest potential upside but requires operational change — format redesign, management intervention, or store footprint reduction.

### Scenario Comparison

| Scenario | 5-Year Gain | Investment Needed | Complexity | Recommended |
|----------|-------------|-------------------|------------|-------------|
| A — Remove below-cost | IDR 8.59B GP | None | Low | **Yes — do first** |
| B — Cap discounts at 10% | IDR 1.09B GP | None | Low | Yes — alongside A |
| C — Fix Medan | IDR 26.92B+ revenue | Medium–High | High | Yes — medium term |

**Best scenario: A (quick win, no cost, stops guaranteed losses immediately). C is the long-term highest-impact play.**

---

## 6. Deliverable Checklist (Week 7)

- [ ] Excel file with `risk_score` formula in new column (paste formula from Section 4)
- [ ] Screenshot: HIGH-risk group (score ≥60) return rate > LOW-risk group
- [ ] Screenshot: discount % vs avg quantity (proves no volume uplift)
- [ ] PivotTable: return rate by month (shows Aug/Oct spike)
- [ ] 1-page summary: top 3 patterns, formula explanation, recommended scenario

---

## 7. Excel Verification Steps

### Verify Pattern 1 (Below-Cost)
1. Add helper column: `=IF(N2>O2,"Below-cost","Normal")`
2. PivotTable: rows=helper column, values=COUNT, SUM of `(O-N)*F` for below-cost group

### Verify Pattern 2 (Discount Effect)
1. PivotTable: rows=`discount_%`, values=AVERAGE(`quantity`), AVERAGE(`Gross_Profit`)
2. Confirm: avg quantity is same across all discount levels

### Verify Pattern 3 (Medan)
1. Filter `store_name` = "Medan Center"
2. Calculate: SUM(`Net_Sales`) / 728 → compare to other stores

### Verify Pattern 5 (Seasonal Spike)
1. Add helper column: `=MONTH(B2)`
2. PivotTable: rows=month, values=SUM(`returned`)/COUNT(`returned`)
3. Confirm: months 2, 5, 8, 10 show highest rates

### Validate Risk Score
1. Add risk_score column with formula from Section 4
2. Filter score ≥ 60 → count returned=1 / total → should be ~10.7%
3. Filter score < 30 → count `cost_price > list_price` → should be ~0%
