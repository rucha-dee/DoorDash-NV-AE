"""
DoorDash New Verticals Analytics Exercise
Python analysis: data cleaning, feature engineering, and regression models M1-M5.

Input : "../New Verticals Analytics Exercise*.xlsx"  (sheet "Dataset")
Output: cleaned ../Data input/delivery_level.csv / item_level.csv
        (consumed unchanged by R_analysis.R), py_m*_coefs.csv coefficient
        tables in this folder, and printed model summaries + a cleaning/
        sample audit trail.

Two modelling conventions that the report needs to state explicitly:

1. WAS_SUBBED is a SUBSET of WAS_MISSING -- a substituted item was, by
   definition, originally missing. "unfulfilled_rate" is therefore
   missing_rate alone (it already includes substituted cases); summing
   missing_rate + sub_rate would double-count every substitution. Asserted
   against the data in the audit below rather than assumed.

2. Standard errors are CLUSTERED BY DASHER throughout. The same dasher
   appears across many deliveries (the top 10% of dashers carry ~60% of
   volume), so treating deliveries as independent understates uncertainty.
"""
from pathlib import Path

import glob
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "Data input"
RAW_FILE = glob.glob(str(ROOT / "*New Verticals Analytics Exercise*.xlsx"))[0]
PERISHABLE = {"Produce", "Dairy & Eggs", "Meat & Fish", "Frozen",
              "Fresh Food", "Bakery", "Ice Cream"}

# Category strings that are the same merchandising concept spelled two ways.
# Left un-merged these enter the item model as separate, thinly-populated
# predictors (e.g. "Baby" n=152 alongside "Baby & Child" n=341).
CATEGORY_ALIASES = {"Baby": "Baby & Child",
                    "Vitamins": "Health",
                    "Storage & Cleaning": "Household"}

RARE_CATEGORY_MIN_N = 150     # below this, pooled into "Other/Rare"
WINSOR_Q = 0.995              # duration outlier cap

rule = "=" * 90


def banner(text):
    print(f"\n{rule}\n{text}\n{rule}")


# ---------------------------------------------------------------------------
# 1. Load & audit the raw file
# ---------------------------------------------------------------------------
banner("1. RAW DATA AUDIT")
raw = pd.read_excel(RAW_FILE, sheet_name="Dataset")
n_rows_raw, n_deliv_raw = len(raw), raw.DELIVERY_UUID.nunique()
print(f"Raw item rows            : {n_rows_raw:,}")
print(f"Raw unique deliveries    : {n_deliv_raw:,}")
print(f"Submarkets               : {raw.DELIV_SUBMARKET.unique().tolist()}")
print(f"Stores                   : {sorted(raw.DELIV_STORE_NAME.unique())}")

# Timezone: the file ships a pre-converted EDT column. Verify it is a true
# UTC-4 shift before trusting it for local-time dayparts.
offset_h = (raw.DELIV_CREATED_AT - raw.DELIV_CREATED_AT_EDT).dt.total_seconds() / 3600
print(f"\nWindow (UTC)             : {raw.DELIV_CREATED_AT.min()} -> {raw.DELIV_CREATED_AT.max()}")
print(f"Window (EDT)             : {raw.DELIV_CREATED_AT_EDT.min()} -> {raw.DELIV_CREATED_AT_EDT.max()}")
print(f"UTC-EDT offset (hours)   : {offset_h.min():.4f} to {offset_h.max():.4f} "
      f"-> {'OK, single -4h EDT shift' if abs(offset_h.mean() - 4) < 0.01 else 'UNEXPECTED'}")
print("All dayparts below are America/New_York local time, not UTC.")

# Flag integrity.
subbed_not_missing = int(((raw.WAS_SUBBED == 1) & (raw.WAS_MISSING == 0)).sum())
unresolved = (raw.WAS_MISSING == 0) & (raw.WAS_FOUND == 0)
print(f"\nWAS_REQUESTED values     : {raw.WAS_REQUESTED.unique().tolist()} (every row is a requested item)")
print(f"WAS_SUBBED=1 & MISSING=0 : {subbed_not_missing} -> substitution IS a strict subset of missing")
assert subbed_not_missing == 0, "WAS_SUBBED is not a subset of WAS_MISSING; revisit unfulfilled_rate"
print(f"Neither found nor missing: {int(unresolved.sum()):,} rows "
      f"({int((unresolved & (raw.WAS_CANCELLED == 1)).sum()):,} of them on cancelled deliveries) "
      "-> unresolved shopping state, not a fulfilment outcome")

# Cancelled deliveries: which fields are structurally undefined?
canc = raw[raw.WAS_CANCELLED == 1]
print(f"\nCancelled deliveries     : {canc.DELIVERY_UUID.nunique():,} "
      f"({100 * canc.DELIVERY_UUID.nunique() / n_deliv_raw:.2f}% of deliveries)")
print(f"  CLAT null              : {100 * canc.DELIV_CLAT.isna().mean():.1f}%")
print(f"  D2R null               : {100 * canc.DELIV_D2R.isna().mean():.1f}%")
print(f"  DASHER_ID null         : {100 * canc.DELIV_DASHER_ID.isna().mean():.1f}%  "
      "<- no cancelled order was EVER assigned a dasher")
print(f"  late flag / MI report  : {canc.DELIV_IS_20_MIN_LATE.mean():.1%} / "
      f"{canc.DELIV_MISSING_INCORRECT_REPORT_BINARY.mean():.1%} (both structurally 0)")

# Duration outliers.
d2r_cap = raw.DELIV_D2R.quantile(WINSOR_Q)
clat_cap = raw.DELIV_CLAT.quantile(WINSOR_Q)
print(f"\nDELIV_D2R  max={raw.DELIV_D2R.max():.1f} min, mean={raw.DELIV_D2R.mean():.2f} "
      f"-> winsorising at p{WINSOR_Q:.3%} = {d2r_cap:.1f} min")
print(f"DELIV_CLAT max={raw.DELIV_CLAT.max():.1f} min, mean={raw.DELIV_CLAT.mean():.2f} "
      f"-> winsorising at p{WINSOR_Q:.3%} = {clat_cap:.1f} min")
print(f"ITEM_PRICE range         : ${raw.ITEM_PRICE.min():.2f} - ${raw.ITEM_PRICE.max():.2f}, "
      f"non-positive: {int((raw.ITEM_PRICE <= 0).sum())}")

# ---------------------------------------------------------------------------
# 2. Clean
# ---------------------------------------------------------------------------
banner("2. CLEANING")
item = raw.copy()

item["ITEM_CATEGORY_RAW"] = item.ITEM_CATEGORY
item["ITEM_CATEGORY"] = item.ITEM_CATEGORY.str.strip().replace(CATEGORY_ALIASES)
n_merged = int((item.ITEM_CATEGORY != item.ITEM_CATEGORY_RAW).sum())
print(f"Category strings normalised: {len(raw.ITEM_CATEGORY.unique())} -> "
      f"{len(item.ITEM_CATEGORY.unique())} distinct ({n_merged:,} rows relabelled via {CATEGORY_ALIASES})")

counts = item.ITEM_CATEGORY.value_counts()
rare = counts[counts < RARE_CATEGORY_MIN_N].index
item["ITEM_CATEGORY_GRP"] = item.ITEM_CATEGORY.where(~item.ITEM_CATEGORY.isin(rare), "Other/Rare")
print(f"Categories with n<{RARE_CATEGORY_MIN_N} pooled into 'Other/Rare': "
      f"{sorted(rare)} ({int(item.ITEM_CATEGORY.isin(rare).sum()):,} rows)")

item["DELIV_D2R"] = item.DELIV_D2R.clip(upper=d2r_cap)
item["DELIV_CLAT"] = item.DELIV_CLAT.clip(upper=clat_cap)

print(f"\nRow count: {n_rows_raw:,} in -> {len(item):,} out (no rows dropped at item level; "
      "cleaning is relabel + winsorise only)")

# ---------------------------------------------------------------------------
# 3. Delivery-level aggregation
# ---------------------------------------------------------------------------
banner("3. FEATURE CONSTRUCTION")
agg = item.groupby("DELIVERY_UUID").agg(
    n_items_requested=("WAS_REQUESTED", "sum"),
    n_missing=("WAS_MISSING", "sum"),
    n_subbed=("WAS_SUBBED", "sum"),
    n_found=("WAS_FOUND", "sum"),
    order_value=("ITEM_PRICE", "sum"),
    avg_item_price=("ITEM_PRICE", "mean"),
    n_categories=("ITEM_CATEGORY", "nunique"),
    has_alcohol=("ITEM_CATEGORY", lambda x: int("Alcohol" in set(x))),
    has_perishable=("ITEM_CATEGORY", lambda x: int(bool(set(x) & PERISHABLE))),
).reset_index()

agg["missing_rate"] = agg.n_missing / agg.n_items_requested
agg["sub_rate"] = agg.n_subbed / agg.n_items_requested
agg["unfulfilled_rate"] = agg.missing_rate          # already includes substituted items
agg["plain_missing_rate"] = agg.missing_rate - agg.sub_rate

deliv = item.drop_duplicates("DELIVERY_UUID")[[
    "DELIVERY_UUID", "DELIV_CREATED_AT_EDT", "DELIV_STORE_NAME", "DELIV_SUBMARKET",
    "DELIV_DASHER_ID", "DELIV_D2R", "DELIV_IS_20_MIN_LATE", "DELIV_CLAT",
    "WAS_CANCELLED", "DELIV_MISSING_INCORRECT_REPORT_BINARY",
]].merge(agg, on="DELIVERY_UUID", how="left")

deliv["hour"] = deliv.DELIV_CREATED_AT_EDT.dt.hour
deliv["dow"] = deliv.DELIV_CREATED_AT_EDT.dt.day_name()
deliv["is_weekend"] = deliv.DELIV_CREATED_AT_EDT.dt.dayofweek >= 5
deliv["daypart"] = pd.cut(
    deliv.hour, bins=[-1, 5, 10, 14, 17, 21, 24],
    labels=["Overnight(0-5)", "Morning(6-10)", "Midday(11-14)",
            "Afternoon(15-17)", "Evening(18-21)", "Night(22-23)"])

# Grocery3 has 188 deliveries and zero complaints, which perfectly separates the
# complaint model. Pooled with Grocery2 for M2 only; kept separate elsewhere.
deliv["STORE_GRP"] = deliv.DELIV_STORE_NAME.replace({"Grocery2": "Grocery2/3",
                                                     "Grocery3": "Grocery2/3"})
deliv["dasher_assigned"] = deliv.DELIV_DASHER_ID.notna().astype(int)

# Clustering unit: the dasher. Deliveries that never got a dasher cannot be
# attributed to one, so each becomes its own singleton cluster.
deliv["cluster_id"] = np.where(
    deliv.DELIV_DASHER_ID.notna(),
    "d" + deliv.DELIV_DASHER_ID.fillna(-1).astype("int64").astype(str),
    "unassigned_" + deliv.DELIVERY_UUID.astype(str))

print(f"Delivery-level table: {len(deliv):,} rows x {deliv.shape[1]} cols")
print(f"Item-level table    : {len(item):,} rows x {item.shape[1]} cols")
print(f"Dayparts (EDT)      : {[str(c) for c in deliv.daypart.cat.categories]}")

item = item.merge(deliv[["DELIVERY_UUID", "cluster_id", "daypart", "is_weekend"]],
                  on="DELIVERY_UUID", how="left")
DATA_DIR.mkdir(parents=True, exist_ok=True)
deliv.to_csv(DATA_DIR / "delivery_level.csv", index=False)
item.to_csv(DATA_DIR / "item_level.csv", index=False)

# ---------------------------------------------------------------------------
# 4. Analysis-sample accounting  (what each model actually sees, and why)
# ---------------------------------------------------------------------------
banner("4. ANALYSIS SAMPLE ACCOUNTING")
completed = deliv[deliv.WAS_CANCELLED == 0].copy()
print(f"All deliveries                    : {len(deliv):,}   (M4 cancellation model)")
print(f"Completed deliveries              : {len(completed):,}   (M1/M2 -- late & complaint "
      "are undefined for cancelled orders)")

drop_m3 = completed.DELIV_CLAT.isna() | completed.DELIV_D2R.isna()
print(f"Completed, missing CLAT or D2R    : {int(drop_m3.sum()):,}   (listwise-dropped by M3/M5)")
print(f"  late rate, DROPPED rows         : {completed[drop_m3].DELIV_IS_20_MIN_LATE.mean():.2%}")
print(f"  late rate, RETAINED rows        : {completed[~drop_m3].DELIV_IS_20_MIN_LATE.mean():.2%}")
print("  -> the dropped rows are ~3x LATER than the modelled ones. M3 is fit on a sample")
print("     that excludes the worst lateness cases; the CLAT coefficient is therefore a")
print("     conservative estimate and the exclusion must be disclosed, not silent.")

unassigned = completed[completed.dasher_assigned == 0]
print(f"\nDASHER-ASSIGNMENT FAILURE (completed deliveries with no dasher ID):")
print(f"  n                               : {len(unassigned):,} ({len(unassigned)/len(completed):.2%} of completed)")
print(f"  late rate                       : {unassigned.DELIV_IS_20_MIN_LATE.mean():.2%}  vs "
      f"{completed[completed.dasher_assigned == 1].DELIV_IS_20_MIN_LATE.mean():.2%} when a dasher is assigned")
print("  -> worst-performing segment in the dataset, and invisible in M3 because these")
print("     rows carry no CLAT. Reported separately as a Dasher-side finding.")

cl = completed.groupby("cluster_id").size().sort_values(ascending=False)
real = cl[~cl.index.str.startswith("unassigned")]
print(f"\nDASHER CLUSTERING PROFILE (justifies clustered SEs):")
print(f"  distinct dashers                : {len(real):,}")
print(f"  median / max deliveries per dasher: {real.median():.0f} / {real.max():,}")
print(f"  share of volume, top 10% dashers: {real.head(int(len(real) * 0.1)).sum() / real.sum():.1%}")

# ---------------------------------------------------------------------------
# 5. Models
# ---------------------------------------------------------------------------
def fit(formula, data, kind="logit", label="", note=""):
    """Fit with dasher-clustered SEs, and report how much clustering moved them."""
    used = [c for c in data.columns if c in formula or c == "cluster_id"]
    sub = data.dropna(subset=[c for c in used if c != "cluster_id"]).copy()
    est = smf.logit if kind == "logit" else smf.ols
    naive = est(formula, data=sub).fit(disp=0, maxiter=200) if kind == "logit" \
        else est(formula, data=sub).fit()
    clustered = est(formula, data=sub).fit(
        cov_type="cluster", cov_kwds={"groups": sub.cluster_id},
        **({"disp": 0, "maxiter": 200} if kind == "logit" else {}))

    banner(f"{label}{('  [' + note + ']') if note else ''}")
    print(clustered.summary())
    fit_stat = (f"Pseudo R2 (McFadden) = {clustered.prsquared:.3f}" if kind == "logit"
                else f"R2 = {clustered.rsquared:.3f} (adj {clustered.rsquared_adj:.3f})")
    print(f"\nN = {int(clustered.nobs):,} | clusters = {sub.cluster_id.nunique():,} | {fit_stat}")

    se_ratio = (clustered.bse / naive.bse).replace([np.inf, -np.inf], np.nan)
    print(f"Clustered/naive SE ratio: median {se_ratio.median():.2f}, max {se_ratio.max():.2f} "
          "(>1 = naive SEs were overconfident)")

    ci = clustered.conf_int()
    ci.columns = ["lo", "hi"]
    out = pd.DataFrame({
        "term": clustered.params.index,
        "coef": clustered.params.values,
        "se_clustered": clustered.bse.values,
        "se_naive": naive.bse.values,
        "p_clustered": clustered.pvalues.values,
        "p_naive": naive.pvalues.values,
    })
    if kind == "logit":
        out["odds_ratio"] = np.exp(clustered.params.values)
        out["or_lo"], out["or_hi"] = np.exp(ci.lo.values), np.exp(ci.hi.values)
    return clustered, out


item_completed = item[item.DELIVERY_UUID.isin(completed.DELIVERY_UUID)].copy()
print(f"\nM1 item sample: {len(item):,} item rows -> {len(item_completed):,} on completed deliveries "
      f"({len(item) - len(item_completed):,} rows on cancelled orders excluded, where only "
      f"{raw[raw.WAS_CANCELLED == 1].WAS_FOUND.mean():.0%} of items were ever resolved)")

m1, c1 = fit(
    "WAS_MISSING ~ C(ITEM_CATEGORY_GRP, Treatment(reference='Drinks')) + ITEM_PRICE "
    "+ C(DELIV_STORE_NAME, Treatment(reference='DashMart1'))",
    item_completed, "logit", "M1 - Item-level: what predicts an item being MISSING?",
    "completed deliveries only")

m2, c2 = fit(
    "DELIV_MISSING_INCORRECT_REPORT_BINARY ~ unfulfilled_rate + n_items_requested + order_value "
    "+ DELIV_IS_20_MIN_LATE + C(STORE_GRP, Treatment(reference='DashMart1')) "
    "+ has_perishable + has_alcohol",
    completed, "logit", "M2 - Delivery-level: what predicts a MISSING/INCORRECT-ITEM COMPLAINT?",
    "completed only; Grocery2/3 pooled to avoid perfect separation")

m3, c3 = fit(
    "DELIV_IS_20_MIN_LATE ~ DELIV_D2R + DELIV_CLAT "
    "+ C(DELIV_STORE_NAME, Treatment(reference='DashMart1')) + n_items_requested + order_value "
    "+ C(daypart, Treatment(reference='Midday(11-14)')) + is_weekend",
    completed, "logit", "M3 - Delivery-level: what predicts a 20+ MIN LATE delivery?",
    "completed only; requires non-null CLAT & D2R")

m4, c4 = fit(
    "WAS_CANCELLED ~ C(DELIV_STORE_NAME, Treatment(reference='DashMart1')) + order_value "
    "+ n_items_requested + C(daypart, Treatment(reference='Midday(11-14)')) + is_weekend "
    "+ has_perishable + has_alcohol",
    deliv, "logit", "M4 - Delivery-level: what predicts a CANCELLATION?", "all deliveries")

m5, c5 = fit(
    "DELIV_CLAT ~ n_items_requested + order_value "
    "+ C(DELIV_STORE_NAME, Treatment(reference='DashMart1')) "
    "+ C(daypart, Treatment(reference='Midday(11-14)')) + is_weekend",
    completed, "ols", "M5 - Delivery-level (OLS): what drives DASHER ACCEPTANCE TIME (CLAT)?",
    "completed only")

for name, tbl in [("m1", c1), ("m2", c2), ("m3", c3), ("m4", c4), ("m5", c5)]:
    tbl.to_csv(f"py_{name}_coefs.csv", index=False)

# ---------------------------------------------------------------------------
# 6. Robustness: does the headline category reversal survive?
# ---------------------------------------------------------------------------
banner("6. ROBUSTNESS - the Simpson's-paradox category reversal")
raw_rate = item_completed.groupby("ITEM_CATEGORY_GRP").WAS_MISSING.mean().mul(100).round(2)
print("Raw unfulfilment %, all stores pooled (the misleading read):")
print(raw_rate.sort_values(ascending=False).head(8).to_string())
print("\nStore-adjusted odds ratios vs Drinks (M1, dasher-clustered SEs):")
for k in ["Produce", "Meat & Fish", "Dairy & Eggs", "Household", "Baby & Child", "Frozen", "Bakery"]:
    hit = [t for t in c1.term if f"T.{k}]" in t]
    if hit:
        r = c1[c1.term == hit[0]].iloc[0]
        print(f"  {k:15s} OR={r.odds_ratio:5.3f}  [{r.or_lo:.3f}, {r.or_hi:.3f}]  p={r.p_clustered:.4f}")
print("\nChannel-mix confound, % of each category sourced from DashMart1:")
mix = (100 * pd.crosstab(item_completed.ITEM_CATEGORY_GRP,
                         item_completed.DELIV_STORE_NAME, normalize="index")).round(1)
print(mix.loc[[c for c in ["Drinks", "Snacks", "Produce", "Meat & Fish"] if c in mix.index],
              "DashMart1"].to_string())

banner("DONE")
print("Wrote Data input/delivery_level.csv, item_level.csv, and py_m1..m5_coefs.csv")
print("Run R_analysis.R next; it consumes these CSVs unchanged for the cross-tool check.")
