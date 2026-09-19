"""
Auria Fashion Group -- Synthetic Data Generator
=================================================
Generates a fully fictional global fashion retail dataset for a Databricks
medallion-architecture / agentic-dashboard portfolio project.

ALL entities, names, and transactions are synthetic. Any resemblance to real
people, companies, or brands is coincidental.

Reproducible: fixed seed (42) -> identical output every run.

Run:
    python3 generate_data.py

Output: CSVs written to ./output/
"""

import numpy as np
import pandas as pd
from faker import Faker
from datetime import date, timedelta
import os

SEED = 42
rng = np.random.default_rng(SEED)
fake = Faker()
Faker.seed(SEED)

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)

START_DATE = date(2022, 1, 1)
TODAY = date(2026, 9, 15)          # "as of" date for this generation run
TOTAL_DAYS = (TODAY - START_DATE).days

def days_to_date(d):
    return START_DATE + timedelta(days=int(d))

def month_start(d):
    return date(d.year, d.month, 1)

def month_range(start, end):
    """List of month-start dates from start to end inclusive."""
    months = []
    cur = date(start.year, start.month, 1)
    while cur <= end:
        months.append(cur)
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return months

ALL_MONTHS = month_range(START_DATE, TODAY)

print(f"Generating Auria Fashion Group synthetic dataset")
print(f"Window: {START_DATE} .. {TODAY}  ({TOTAL_DAYS} days, {len(ALL_MONTHS)} months)")

# ---------------------------------------------------------------------------
# 1. REFERENCE / GEOGRAPHY DATA
# ---------------------------------------------------------------------------

# region -> [(country, currency, [cities...], store_weight)]
GEO = {
    "North America": [
        ("United States", "USD", ["New York", "Los Angeles", "Chicago", "Miami", "Dallas", "San Francisco"], 3),
        ("Canada", "CAD", ["Toronto", "Vancouver"], 2),
    ],
    "Europe": [
        ("United Kingdom", "GBP", ["London", "Manchester"], 3),
        ("Germany", "EUR", ["Berlin", "Munich"], 2),
        ("France", "EUR", ["Paris", "Lyon"], 2),
        ("Italy", "EUR", ["Milan", "Rome"], 2),
        ("Spain", "EUR", ["Madrid", "Barcelona"], 2),
    ],
    "Asia": [
        ("Japan", "JPY", ["Tokyo", "Osaka"], 2),
        ("India", "INR", ["Mumbai", "Delhi", "Bangalore"], 3),
        ("Singapore", "SGD", ["Singapore"], 1),
        ("South Korea", "KRW", ["Seoul"], 2),
    ],
}

REGIONS = list(GEO.keys())

COUNTRY_TO_REGION = {}
COUNTRY_TO_CURRENCY = {}
COUNTRY_CITIES = {}
for region, countries in GEO.items():
    for country, currency, cities, weight in countries:
        COUNTRY_TO_REGION[country] = region
        COUNTRY_TO_CURRENCY[country] = currency
        COUNTRY_CITIES[country] = cities

CURRENCIES = sorted(set(COUNTRY_TO_CURRENCY.values()) | {"USD"})

print(f"Regions: {REGIONS}")
print(f"Currencies: {CURRENCIES}")

# ---------------------------------------------------------------------------
# 2. EXCHANGE RATES  (value of 1 unit of currency, in USD; month-end)
# ---------------------------------------------------------------------------

BASE_RATE = {
    "USD": 1.0000,
    "EUR": 1.08,
    "GBP": 1.25,
    "CAD": 0.735,
    "INR": 0.0119,   # ~84 INR / USD
    "JPY": 0.0067,   # ~150 JPY / USD
    "SGD": 0.735,
    "KRW": 0.00072,  # ~1390 KRW / USD
}

fx_rows = []
for ccy in CURRENCIES:
    rate = BASE_RATE[ccy]
    for m in ALL_MONTHS:
        if ccy != "USD":
            # small random walk +/- 0.6% per month, mean-reverting toward BASE_RATE
            drift = rng.normal(0, 0.006)
            reversion = (BASE_RATE[ccy] - rate) * 0.03
            rate = max(rate * (1 + drift) + reversion, BASE_RATE[ccy] * 0.75)
        fx_rows.append({"rate_month": m.isoformat(), "currency": ccy, "rate_to_usd": round(rate, 6)})

exchange_rates = pd.DataFrame(fx_rows)
print(f"exchange_rates: {len(exchange_rates)} rows")

FX_LOOKUP = {(r["rate_month"], r["currency"]): r["rate_to_usd"] for r in fx_rows}

def fx_rate(d, ccy):
    """USD value of 1 unit of `ccy` for the month containing date `d`."""
    key = (month_start(d).isoformat(), ccy)
    return FX_LOOKUP.get(key, BASE_RATE[ccy])

# ---------------------------------------------------------------------------
# 3. SUPPLIERS
# ---------------------------------------------------------------------------

suppliers = pd.DataFrame([
    {"supplier_id": "SUP001", "supplier_name": "Meridian Textile Works", "country": "Vietnam", "region": "Asia",
     "category_focus": "Apparel Manufacturing", "avg_lead_time_days": 28, "lead_time_stddev_days": 6, "reliability_score": 0.90},
    {"supplier_id": "SUP002", "supplier_name": "Solara Garment Co.", "country": "India", "region": "Asia",
     "category_focus": "Textiles & Woven Goods", "avg_lead_time_days": 24, "lead_time_stddev_days": 5, "reliability_score": 0.88},
    {"supplier_id": "SUP003", "supplier_name": "Norrland Leather & Footwear", "country": "Portugal", "region": "Europe",
     "category_focus": "Footwear & Leather Goods", "avg_lead_time_days": 18, "lead_time_stddev_days": 4, "reliability_score": 0.93},
    {"supplier_id": "SUP004", "supplier_name": "Cascade Knitting Mills", "country": "Mexico", "region": "North America",
     "category_focus": "Knitwear & Accessories", "avg_lead_time_days": 14, "lead_time_stddev_days": 3, "reliability_score": 0.95},
])
print(f"suppliers: {len(suppliers)} rows")

# ---------------------------------------------------------------------------
# 4. PRODUCTS
# ---------------------------------------------------------------------------

CATEGORIES = {
    "Outerwear":  {"sub": ["Coats", "Jackets", "Parkas"], "price": (120, 420), "supplier": "SUP001", "season": "cold"},
    "Tops":       {"sub": ["Shirts", "Blouses", "Sweaters"], "price": (35, 140), "supplier": "SUP002", "season": "all"},
    "Bottoms":    {"sub": ["Trousers", "Jeans", "Skirts"], "price": (45, 160), "supplier": "SUP002", "season": "all"},
    "Dresses":    {"sub": ["Casual Dresses", "Evening Dresses"], "price": (70, 260), "supplier": "SUP001", "season": "warm"},
    "Footwear":   {"sub": ["Boots", "Sneakers", "Sandals"], "price": (60, 240), "supplier": "SUP003", "season": "all"},
    "Accessories":{"sub": ["Bags", "Scarves", "Belts"], "price": (25, 180), "supplier": "SUP004", "season": "all"},
}

ADJ = ["Classic", "Modern", "Heritage", "Urban", "Essential", "Signature", "Coastal", "Alpine", "Studio", "Everyday"]
MATERIAL = ["Wool", "Cotton", "Linen", "Leather", "Merino", "Denim", "Silk", "Knit", "Suede", "Poplin"]

def gen_product_name(category, sub):
    return f"{rng.choice(ADJ)} {rng.choice(MATERIAL)} {sub.rstrip('s') if sub.endswith('s') else sub}"

products = []
pid = 1
n_products = 50
cats = list(CATEGORIES.keys())
for i in range(n_products):
    cat = cats[i % len(cats)]
    info = CATEGORIES[cat]
    sub = rng.choice(info["sub"])
    lo, hi = info["price"]
    unit_price = round(rng.uniform(lo, hi), 2)
    unit_cost = round(unit_price * rng.uniform(0.35, 0.55), 2)  # ~45-65% gross margin at list price
    # 70% of products already exist at window start; 30% launch progressively (new collections)
    if rng.random() < 0.70:
        launch_date = START_DATE - timedelta(days=int(rng.integers(30, 900)))  # existed before window
    else:
        launch_day_offset = int(rng.integers(0, TOTAL_DAYS - 60))
        launch_date = days_to_date(launch_day_offset)
    # ~10% discontinued at some point after launch (at least 9 months after launch, before today)
    discontinued_date = None
    earliest_disc = max(launch_date, START_DATE) + timedelta(days=270)
    if rng.random() < 0.10 and earliest_disc < TODAY - timedelta(days=30):
        disc_offset = int(rng.integers(0, (TODAY - earliest_disc).days))
        discontinued_date = earliest_disc + timedelta(days=disc_offset)
    products.append({
        "product_id": f"SKU{pid:04d}",
        "product_name": gen_product_name(cat, sub),
        "category": cat,
        "sub_category": sub,
        "gender": rng.choice(["Women", "Men", "Unisex"], p=[0.5, 0.35, 0.15]),
        "supplier_id": info["supplier"],
        "season_affinity": info["season"],
        "size_range": "XS-XL" if cat != "Footwear" else "36-45",
        "unit_cost_usd": unit_cost,
        "unit_price_usd": unit_price,
        "launch_date": launch_date.isoformat(),
        "discontinued_date": discontinued_date.isoformat() if discontinued_date else "",
    })
    pid += 1

products = pd.DataFrame(products)
print(f"products: {len(products)} rows")

# ---------------------------------------------------------------------------
# 5. STORES
# ---------------------------------------------------------------------------

stores = []
sid = 1
STORE_TO_WAREHOUSE = {}
for region, countries in GEO.items():
    for country, currency, cities, weight in countries:
        for city in cities:
            n_stores_here = 1 if weight <= 1 else rng.integers(1, weight + 1)
            for k in range(n_stores_here):
                store_id = f"STR{sid:03d}"
                opened_offset = int(rng.integers(0, min(TOTAL_DAYS, 1400)))
                opened_date = min(START_DATE + timedelta(days=opened_offset), TODAY - timedelta(days=60))
                stores.append({
                    "store_id": store_id,
                    "store_name": f"Auria {city}" + (f" #{k+1}" if n_stores_here > 1 else ""),
                    "region": region,
                    "country": country,
                    "city": city,
                    "currency": currency,
                    "store_type": rng.choice(["Flagship", "Standard", "Outlet"], p=[0.15, 0.65, 0.20]),
                    "opened_date": opened_date.isoformat(),
                })
                sid += 1

stores = pd.DataFrame(stores)
print(f"stores: {len(stores)} rows")

# ---------------------------------------------------------------------------
# 6. WAREHOUSES  (one regional DC per region, plus a second DC for the two
#    largest regions so replenishment realistically fans out)
# ---------------------------------------------------------------------------

warehouses = pd.DataFrame([
    {"warehouse_id": "WH01", "warehouse_name": "Auria DC - New Jersey", "region": "North America", "country": "United States", "city": "Newark"},
    {"warehouse_id": "WH02", "warehouse_name": "Auria DC - Ontario", "region": "North America", "country": "Canada", "city": "Toronto"},
    {"warehouse_id": "WH03", "warehouse_name": "Auria DC - Rotterdam", "region": "Europe", "country": "Netherlands", "city": "Rotterdam"},
    {"warehouse_id": "WH04", "warehouse_name": "Auria DC - Milan", "region": "Europe", "country": "Italy", "city": "Milan"},
    {"warehouse_id": "WH05", "warehouse_name": "Auria DC - Osaka", "region": "Asia", "country": "Japan", "city": "Osaka"},
    {"warehouse_id": "WH06", "warehouse_name": "Auria DC - Mumbai", "region": "Asia", "country": "India", "city": "Mumbai"},
    {"warehouse_id": "WH07", "warehouse_name": "Auria DC - Singapore", "region": "Asia", "country": "Singapore", "city": "Singapore"},
])
print(f"warehouses: {len(warehouses)} rows")

WAREHOUSES_BY_REGION = {r: warehouses[warehouses.region == r].warehouse_id.tolist() for r in REGIONS}

# Assign each store to its nearest (same-region, round-robin) warehouse
store_wh_list = []
region_counters = {r: 0 for r in REGIONS}
for _, s in stores.iterrows():
    whs = WAREHOUSES_BY_REGION[s.region]
    wh = whs[region_counters[s.region] % len(whs)]
    region_counters[s.region] += 1
    store_wh_list.append(wh)
stores["home_warehouse_id"] = store_wh_list

print("Reference data complete.\n")

# ---------------------------------------------------------------------------
# 7. CUSTOMERS
# ---------------------------------------------------------------------------

N_CUSTOMERS = 2000
REGION_SHARE = {"North America": 0.40, "Europe": 0.35, "Asia": 0.25}

# Build a flat weighted list of (country, currency) pulled from GEO's city/weight info
country_weight = []
for region, countries in GEO.items():
    for country, currency, cities, weight in countries:
        country_weight.append((region, country, currency, weight))

customers = []
ACQ_CHANNELS = ["Organic Search", "Paid Social", "Referral", "In-Store Signup", "Email Campaign", "Direct"]
for i in range(1, N_CUSTOMERS + 1):
    region = rng.choice(list(REGION_SHARE.keys()), p=list(REGION_SHARE.values()))
    candidates = [c for c in country_weight if c[0] == region]
    weights = np.array([c[3] for c in candidates], dtype=float)
    weights /= weights.sum()
    _, country, currency, _ = candidates[rng.choice(len(candidates), p=weights)]
    city = rng.choice(COUNTRY_CITIES[country])
    signup_offset = int(rng.integers(0, TOTAL_DAYS))
    signup_date = days_to_date(signup_offset)
    gender_for_name = rng.choice(["M", "F"])
    first = fake.first_name_male() if gender_for_name == "M" else fake.first_name_female()
    last = fake.last_name()
    customers.append({
        "customer_id": f"CUST{i:05d}",
        "first_name": first,
        "last_name": last,
        "email": f"{first.lower()}.{last.lower()}{i}@example-fake.test",
        "region": region,
        "country": country,
        "city": city,
        "home_currency": currency,
        "acquisition_channel": rng.choice(ACQ_CHANNELS, p=[0.28, 0.20, 0.14, 0.16, 0.14, 0.08]),
        "signup_date": signup_date.isoformat(),
        "is_active": bool(rng.random() < 0.88),
    })

customers = pd.DataFrame(customers)
print(f"customers: {len(customers)} rows")

# Pre-compute a repeat-purchase propensity per customer (skew: a core of loyal
# repeat buyers, a long tail of one-time/occasional buyers) -- used when
# sampling orders. Lognormal gives a realistic skew without the runaway
# extreme tail a Pareto distribution would produce (no single "mega-customer"
# accounting for an implausible share of all orders).
raw_weight = rng.lognormal(mean=0.0, sigma=0.85, size=len(customers))
customers["purchase_weight"] = np.clip(raw_weight, 0.08, 10.0)

# ---------------------------------------------------------------------------
# 8. PROMOTIONS
# ---------------------------------------------------------------------------

PROMO_NAMES = ["Spring Refresh", "Summer Sale", "Back to Campus", "Autumn Layers",
               "Holiday Gifting", "Winter Clearance", "Members Early Access", "Flash Weekend"]

promotions = []
promo_id = 1
for year in range(2022, 2027):
    for name in PROMO_NAMES:
        if rng.random() < 0.55:  # not every campaign runs every year
            start_offset = int(rng.integers(0, 340))
            start = date(year, 1, 1) + timedelta(days=start_offset)
            if start > TODAY:
                continue
            length = int(rng.integers(5, 21))
            end = min(start + timedelta(days=length), TODAY)
            promotions.append({
                "promotion_id": f"PROMO{promo_id:04d}",
                "promotion_name": f"{name} {year}",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "discount_pct": round(rng.uniform(0.10, 0.35), 2),
                "scope_region": rng.choice(REGIONS + ["All"], p=[0.2, 0.2, 0.2, 0.4]),
            })
            promo_id += 1

promotions = pd.DataFrame(promotions)
print(f"promotions: {len(promotions)} rows")

def active_promotions(d):
    mask = (promotions.start_date <= d.isoformat()) & (promotions.end_date >= d.isoformat())
    return promotions[mask]

# Fast lookup: date-string -> discount_pct (max concurrent promo) and scope_region
PROMO_BY_DAY = {}
for _, p in promotions.iterrows():
    sd, ed = date.fromisoformat(p.start_date), date.fromisoformat(p.end_date)
    d = sd
    while d <= ed:
        PROMO_BY_DAY.setdefault(d.isoformat(), []).append(p)
        d += timedelta(days=1)

def promo_for(d, region):
    cands = PROMO_BY_DAY.get(d.isoformat(), [])
    cands = [p for p in cands if p.scope_region in ("All", region)]
    if not cands:
        return None, 0.0
    best = max(cands, key=lambda p: p.discount_pct)
    return best.promotion_id, float(best.discount_pct)

# ---------------------------------------------------------------------------
# 9. ORDERS + ORDER ITEMS
# ---------------------------------------------------------------------------

N_ORDERS = 30000

# Seasonality multiplier by month-of-year (retail calendar: Nov/Dec peak,
# Jan trough, back-to-school bump in Aug/Sep)
MONTH_SEASONALITY = {1: 0.72, 2: 0.78, 3: 0.90, 4: 0.95, 5: 1.00, 6: 0.98,
                      7: 0.92, 8: 1.08, 9: 1.10, 10: 1.05, 11: 1.55, 12: 1.70}

# YoY growth trend: the business is growing
YEAR_GROWTH = {2022: 0.85, 2023: 0.95, 2024: 1.05, 2025: 1.15, 2026: 1.20}

def day_weight(d):
    w = MONTH_SEASONALITY[d.month] * YEAR_GROWTH[d.year]
    # mild day-of-week lift for weekends (in-store) handled at channel level below
    return w

day_offsets = np.arange(TOTAL_DAYS)
day_dates = [days_to_date(o) for o in day_offsets]
day_weights = np.array([day_weight(d) for d in day_dates])
day_probs = day_weights / day_weights.sum()

active_customers = customers.copy()
cust_probs = (active_customers["purchase_weight"] / active_customers["purchase_weight"].sum()).values
# Safety cap: no single customer's sampling probability may imply more than
# ~0.6% of all orders (~180 orders over 4.7 years -- a very active but
# plausible repeat shopper), so the lognormal skew can't produce a runaway
# "mega-customer" outlier.
cust_probs = np.minimum(cust_probs, 0.006)
cust_probs = cust_probs / cust_probs.sum()

REGION_CHANNEL_ONLINE_SHARE = {"North America": 0.62, "Europe": 0.55, "Asia": 0.68}

orders = []
order_items = []
oid = 1
oiid = 1

order_days = rng.choice(day_offsets, size=N_ORDERS, p=day_probs)
order_cust_idx = rng.choice(len(active_customers), size=N_ORDERS, p=cust_probs)

cust_records = active_customers.to_dict("records")

# products available as of a given day, indexed for fast filtering
products_records = products.to_dict("records")

def products_available_on(d):
    ds = d.isoformat()
    return [p for p in products_records
            if p["launch_date"] <= ds and (p["discontinued_date"] == "" or p["discontinued_date"] > ds)]

# Pre-bucket available products by month to avoid recomputing per-order
AVAILABLE_BY_MONTH = {}
for m in ALL_MONTHS:
    AVAILABLE_BY_MONTH[m.isoformat()] = products_available_on(m)

PAYMENT_METHODS = ["Credit Card", "Debit Card", "Digital Wallet", "Gift Card"]

for i in range(N_ORDERS):
    d = day_dates[order_days[i]]
    cust = cust_records[order_cust_idx[i]]
    region = cust["region"]
    country = cust["country"]
    ccy = cust["home_currency"]

    is_online = rng.random() < REGION_CHANNEL_ONLINE_SHARE[region]
    if is_online:
        channel = "Online"
        store_id = ""
        home_wh = rng.choice(WAREHOUSES_BY_REGION[region])
    else:
        channel = "In-Store"
        region_stores = stores[stores.region == region]
        srow = region_stores.sample(1, random_state=int(rng.integers(0, 1_000_000))).iloc[0]
        store_id = srow.store_id
        home_wh = srow.home_warehouse_id

    order_status = "Cancelled" if rng.random() < 0.02 else "Completed"
    promo_id, promo_discount = promo_for(d, region)

    order_id = f"ORD{oid:06d}"
    orders.append({
        "order_id": order_id,
        "order_date": d.isoformat(),
        "customer_id": cust["customer_id"],
        "channel": channel,
        "store_id": store_id,
        "fulfilling_warehouse_id": home_wh,
        "currency": ccy,
        "promotion_id": promo_id or "",
        "order_status": order_status,
        "payment_method": rng.choice(PAYMENT_METHODS, p=[0.55, 0.25, 0.15, 0.05]),
    })

    avail = AVAILABLE_BY_MONTH[month_start(d).isoformat()]
    # month-level cache is launch-safe but not discontinue-safe mid-month; refine to the exact day
    ds_exact = d.isoformat()
    avail = [p for p in avail if p["discontinued_date"] == "" or p["discontinued_date"] > ds_exact]
    if not avail:
        oid += 1
        continue

    # regional/seasonal category weighting
    month = d.month
    cold_season = month in (11, 12, 1, 2, 3)
    warm_season = month in (5, 6, 7, 8)

    def cat_weight(p):
        w = 1.0
        if p["season_affinity"] == "cold" and cold_season:
            w *= 1.8
        if p["season_affinity"] == "warm" and warm_season:
            w *= 1.7
        if region == "Asia" and p["category"] == "Outerwear":
            w *= 0.6   # lighter outerwear demand in warmer/varied Asian markets
        if region == "North America" and p["category"] == "Footwear":
            w *= 1.15
        return w

    weights = np.array([cat_weight(p) for p in avail])
    weights = weights / weights.sum()

    n_lines_choices = [1, 2, 3, 4, 5]
    n_lines_probs = [0.25, 0.30, 0.25, 0.15, 0.05]
    n_lines = int(rng.choice(n_lines_choices, p=n_lines_probs))
    n_lines = min(n_lines, len(avail))
    chosen_idx = rng.choice(len(avail), size=n_lines, replace=False, p=weights)

    for idx in chosen_idx:
        p = avail[idx]
        qty = int(rng.choice([1, 2, 3], p=[0.75, 0.20, 0.05]))
        unit_price_usd = p["unit_price_usd"]
        unit_price_local = round(unit_price_usd / fx_rate(d, ccy), 2) if ccy != "USD" else unit_price_usd
        line_discount = promo_discount if promo_id else (0.0 if rng.random() > 0.08 else round(rng.uniform(0.05, 0.15), 2))
        order_items.append({
            "order_item_id": f"OI{oiid:07d}",
            "order_id": order_id,
            "product_id": p["product_id"],
            "quantity": qty,
            "unit_price_local": unit_price_local,
            "discount_pct": line_discount,
            "line_net_amount_local": round(qty * unit_price_local * (1 - line_discount), 2),
        })
        oiid += 1

    oid += 1
    if oid % 5000 == 0:
        print(f"  ... generated {oid} orders")

orders = pd.DataFrame(orders)
order_items = pd.DataFrame(order_items)
print(f"orders: {len(orders)} rows")
print(f"order_items: {len(order_items)} rows  (avg {len(order_items)/len(orders):.2f} lines/order)")

# ---------------------------------------------------------------------------
# 10. RETURNS
# ---------------------------------------------------------------------------

oi_join = order_items.merge(orders[["order_id", "order_date", "order_status", "currency", "fulfilling_warehouse_id"]],
                             on="order_id", how="left")
eligible = oi_join[oi_join.order_status == "Completed"].copy()
eligible["order_date_d"] = pd.to_datetime(eligible["order_date"])

RETURN_RATE = 0.035  # ~3.5% of eligible order lines are returned
RETURN_REASONS = ["Size / Fit", "Changed Mind", "Damaged / Defective", "Wrong Item Shipped", "Quality Concern"]
RETURN_REASON_P = [0.40, 0.25, 0.15, 0.10, 0.10]

returns = []
rid = 1
ret_sample = eligible.sample(frac=RETURN_RATE, random_state=SEED)
for _, row in ret_sample.iterrows():
    max_window = min(45, (TODAY - row["order_date_d"].date()).days)
    if max_window <= 1:
        continue
    return_offset = int(rng.integers(2, max_window + 1))
    return_date = row["order_date_d"].date() + timedelta(days=return_offset)
    reason = rng.choice(RETURN_REASONS, p=RETURN_REASON_P)
    qty_returned = min(row["quantity"], int(rng.integers(1, row["quantity"] + 1)))
    unit_price = row["unit_price_local"] * (1 - row["discount_pct"])
    returns.append({
        "return_id": f"RET{rid:06d}",
        "order_item_id": row["order_item_id"],
        "return_date": return_date.isoformat(),
        "quantity_returned": qty_returned,
        "reason": reason,
        "refund_amount_local": round(qty_returned * unit_price, 2),
        "restocked": bool(reason != "Damaged / Defective" and rng.random() < 0.85),
    })
    rid += 1

returns = pd.DataFrame(returns)
print(f"returns: {len(returns)} rows ({len(returns)/len(order_items)*100:.1f}% of order lines)")

# ---------------------------------------------------------------------------
# 11. PURCHASE ORDERS + PURCHASE ORDER LINES
# ---------------------------------------------------------------------------

SUPPLIER_PRODUCTS = {sup_id: products[products.supplier_id == sup_id].to_dict("records")
                     for sup_id in suppliers.supplier_id}

purchase_orders = []
po_lines = []
po_num = 1
po_line_num = 1

for _, wh in warehouses.iterrows():
    for _, sup in suppliers.iterrows():
        sup_products = SUPPLIER_PRODUCTS[sup.supplier_id]
        if not sup_products:
            continue
        earliest_launch = min(date.fromisoformat(p["launch_date"]) for p in sup_products)
        po_start = max(START_DATE, earliest_launch)
        # replenishment cadence: ~10-16 days between POs from this warehouse to this supplier
        cursor = po_start
        while cursor < TODAY - timedelta(days=int(sup.avg_lead_time_days)):
            lead = max(1, int(rng.normal(sup.avg_lead_time_days, sup.lead_time_stddev_days)))
            order_date = cursor
            expected_date = order_date + timedelta(days=lead)
            on_time = rng.random() < sup.reliability_score
            if expected_date > TODAY:
                received_date = None
                status = "Open"
            elif on_time:
                received_date = expected_date
                status = "Received"
            else:
                delay = int(rng.integers(2, 12))
                received_date = min(expected_date + timedelta(days=delay), TODAY)
                status = "Received (Late)"

            avail = [p for p in sup_products
                     if p["launch_date"] <= order_date.isoformat()
                     and (p["discontinued_date"] == "" or p["discontinued_date"] > order_date.isoformat())]
            if avail:
                po_id = f"PO{po_num:05d}"
                purchase_orders.append({
                    "po_id": po_id,
                    "supplier_id": sup.supplier_id,
                    "warehouse_id": wh.warehouse_id,
                    "order_date": order_date.isoformat(),
                    "expected_date": expected_date.isoformat(),
                    "received_date": received_date.isoformat() if received_date else "",
                    "status": status,
                })
                n_lines = min(len(avail), int(rng.integers(1, 4)))
                chosen = rng.choice(len(avail), size=n_lines, replace=False)
                for idx in chosen:
                    p = avail[idx]
                    qty = int(rng.integers(20, 60))
                    po_lines.append({
                        "po_line_id": f"POL{po_line_num:06d}",
                        "po_id": po_id,
                        "product_id": p["product_id"],
                        "quantity": qty,
                        "unit_cost_usd": p["unit_cost_usd"],
                    })
                    po_line_num += 1
                po_num += 1

            interval = int(rng.integers(13, 21))
            cursor = cursor + timedelta(days=interval)

purchase_orders = pd.DataFrame(purchase_orders)
po_lines = pd.DataFrame(po_lines)
print(f"purchase_orders: {len(purchase_orders)} rows")
print(f"purchase_order_lines: {len(po_lines)} rows")

# ---------------------------------------------------------------------------
# 12. INVENTORY MOVEMENTS + MONTHLY SNAPSHOTS
#     (derived entirely from the transactions above -> single source of
#      truth, no double counting between orders / returns / inventory)
# ---------------------------------------------------------------------------

movement_rows = []
mv_id = 1

def next_mv_id():
    global mv_id
    v = f"MOV{mv_id:07d}"
    mv_id += 1
    return v

# 12a. Initial stock injection per (warehouse, product) at first availability
for _, wh in warehouses.iterrows():
    for p in products_records:
        start_d = max(date.fromisoformat(p["launch_date"]), START_DATE)
        if start_d > TODAY:
            continue
        movement_rows.append({
            "movement_id": next_mv_id(), "movement_date": start_d.isoformat(),
            "warehouse_id": wh.warehouse_id, "product_id": p["product_id"],
            "movement_type": "Initial Stock", "quantity_delta": int(rng.integers(30, 70)),
            "reference_id": "",
        })

# 12b. PO receipts (inbound)
received_lines = po_lines.merge(purchase_orders[["po_id", "warehouse_id", "received_date", "status"]], on="po_id")
received_lines = received_lines[received_lines.status.str.startswith("Received")]
for _, r in received_lines.iterrows():
    movement_rows.append({
        "movement_id": next_mv_id(), "movement_date": r.received_date,
        "warehouse_id": r.warehouse_id, "product_id": r.product_id,
        "movement_type": "PO Receipt", "quantity_delta": int(r.quantity),
        "reference_id": r.po_id,
    })

# 12c. Order fulfillment (outbound) -- completed orders only
completed_items = order_items.merge(
    orders[["order_id", "order_date", "order_status", "fulfilling_warehouse_id"]], on="order_id")
completed_items = completed_items[completed_items.order_status == "Completed"]
for _, r in completed_items.iterrows():
    movement_rows.append({
        "movement_id": next_mv_id(), "movement_date": r.order_date,
        "warehouse_id": r.fulfilling_warehouse_id, "product_id": r.product_id,
        "movement_type": "Sale Fulfillment", "quantity_delta": -int(r.quantity),
        "reference_id": r.order_id,
    })

# 12d. Return restocks (inbound, only when marked restocked)
if len(returns):
    ret_join = returns[returns.restocked].merge(
        order_items[["order_item_id", "product_id"]], on="order_item_id").merge(
        orders[["order_id", "fulfilling_warehouse_id"]].merge(
            order_items[["order_id", "order_item_id"]], on="order_id"),
        on="order_item_id")
    for _, r in ret_join.iterrows():
        movement_rows.append({
            "movement_id": next_mv_id(), "movement_date": r.return_date,
            "warehouse_id": r.fulfilling_warehouse_id, "product_id": r.product_id,
            "movement_type": "Return Restock", "quantity_delta": int(r.quantity_returned),
            "reference_id": r.return_id,
        })

inventory_movements = pd.DataFrame(movement_rows)
inventory_movements["date_dt"] = pd.to_datetime(inventory_movements["movement_date"])
inventory_movements.sort_values(["warehouse_id", "product_id", "date_dt"], inplace=True)
inventory_movements["running_stock"] = inventory_movements.groupby(
    ["warehouse_id", "product_id"])["quantity_delta"].cumsum()
print(f"inventory_movements: {len(inventory_movements)} rows")

snapshot_rows = []
for (wh, pid), g in inventory_movements.groupby(["warehouse_id", "product_id"]):
    g = g.copy()
    g["ym"] = g["date_dt"].dt.to_period("M")
    monthly = g.groupby("ym")["running_stock"].agg(["last", "min"])
    start_period = g["ym"].min()
    end_period = pd.Period(TODAY, freq="M")
    full_index = pd.period_range(start=start_period, end=end_period, freq="M")
    monthly = monthly.reindex(full_index)
    monthly["last"] = monthly["last"].ffill()
    monthly["min"] = monthly["min"].fillna(monthly["last"])
    for period, row in monthly.iterrows():
        stock_on_hand = max(0, row["last"])
        snapshot_rows.append({
            "snapshot_month": period.start_time.date().isoformat(),
            "warehouse_id": wh,
            "product_id": pid,
            "stock_on_hand": int(round(stock_on_hand)),
            "stockout_flag": bool(row["min"] <= 0),
        })

inventory_snapshots = pd.DataFrame(snapshot_rows)
inventory_movements.drop(columns=["date_dt", "running_stock"], inplace=True)
print(f"inventory_snapshots: {len(inventory_snapshots)} rows "
      f"({inventory_snapshots.stockout_flag.mean()*100:.1f}% of rows flagged as stockout months)")

# ---------------------------------------------------------------------------
# 13. VALIDATION -- referential integrity + sanity checks
# ---------------------------------------------------------------------------

print("\n--- Validation ---")

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}")
    if not condition:
        raise AssertionError(name)

check("order_items.order_id all exist in orders",
      order_items.order_id.isin(orders.order_id).all())
check("order_items.product_id all exist in products",
      order_items.product_id.isin(products.product_id).all())
check("orders.customer_id all exist in customers",
      orders.customer_id.isin(customers.customer_id).all())
check("orders.fulfilling_warehouse_id all exist in warehouses",
      orders.fulfilling_warehouse_id.isin(warehouses.warehouse_id).all())
check("non-empty orders.store_id all exist in stores",
      orders.loc[orders.store_id != "", "store_id"].isin(stores.store_id).all())
check("returns.order_item_id all exist in order_items",
      returns.order_item_id.isin(order_items.order_item_id).all())
check("purchase_order_lines.po_id all exist in purchase_orders",
      po_lines.po_id.isin(purchase_orders.po_id).all())
check("purchase_order_lines.product_id all exist in products",
      po_lines.product_id.isin(products.product_id).all())
check("purchase_orders.supplier_id all exist in suppliers",
      purchase_orders.supplier_id.isin(suppliers.supplier_id).all())
check("purchase_orders.warehouse_id all exist in warehouses",
      purchase_orders.warehouse_id.isin(warehouses.warehouse_id).all())
check("inventory_movements.warehouse_id all exist in warehouses",
      inventory_movements.warehouse_id.isin(warehouses.warehouse_id).all())
check("inventory_movements.product_id all exist in products",
      inventory_movements.product_id.isin(products.product_id).all())
check("inventory_snapshots.stock_on_hand never negative",
      (inventory_snapshots.stock_on_hand >= 0).all())
check("exchange_rates covers every currency x month",
      len(exchange_rates) == len(CURRENCIES) * len(ALL_MONTHS))

oi_prod = order_items.merge(orders[["order_id", "order_date"]], on="order_id").merge(
    products[["product_id", "launch_date", "discontinued_date"]], on="product_id")
check("no order line before its product's launch_date",
      (oi_prod.order_date >= oi_prod.launch_date).all())
check("no order line after its product's discontinued_date",
      ((oi_prod.discontinued_date == "") | (oi_prod.order_date <= oi_prod.discontinued_date)).all())

# Quick business-sanity summary (not a hard check, just visibility)
oi_usd = order_items.merge(orders[["order_id", "currency", "order_date", "order_status"]], on="order_id")
oi_usd = oi_usd[oi_usd.order_status == "Completed"]
oi_usd["fx"] = oi_usd.apply(lambda r: fx_rate(date.fromisoformat(r.order_date), r.currency), axis=1)
oi_usd["net_amount_usd"] = oi_usd.line_net_amount_local * oi_usd.fx
by_year = oi_usd.groupby(oi_usd.order_date.str[:4])["net_amount_usd"].sum().round(0)
print("\nGross revenue (USD, completed orders) by year:")
print(by_year.to_string())

# ---------------------------------------------------------------------------
# 14. WRITE CSVs
# ---------------------------------------------------------------------------

TABLES = {
    "customers": customers.drop(columns=["purchase_weight"]),
    "products": products,
    "suppliers": suppliers,
    "stores": stores,
    "warehouses": warehouses,
    "orders": orders,
    "order_items": order_items,
    "returns": returns,
    "purchase_orders": purchase_orders,
    "purchase_order_lines": po_lines,
    "inventory_movements": inventory_movements,
    "inventory_snapshots": inventory_snapshots,
    "exchange_rates": exchange_rates,
    "promotions": promotions,
}

print("\n--- Writing CSVs ---")
for name, df in TABLES.items():
    path = os.path.join(OUT_DIR, f"{name}.csv")
    df.to_csv(path, index=False)
    print(f"{name:24s} {len(df):>8,d} rows  -> {path}")

print("\nDone. All identities and transactions above are entirely FICTIONAL, "
      "generated for a portfolio demonstration.")
