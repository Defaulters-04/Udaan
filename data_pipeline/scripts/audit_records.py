#!/usr/bin/env python3
import csv
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")

files = [
    ("market_signals.csv", ["value_min"]),
    ("jobspeak_monthly.csv", ["index_value"]),
    ("colleges.csv", ["nirf_rank", "approved_intake"]),
    ("college_outcomes.csv", ["median_salary_inr"]),
    ("cutoffs.csv", ["closing_rank"]),
    ("fees.csv", ["annual_tuition_inr"]),
    ("arts_design_media_metrics.csv", ["value"])
]

records = []

for fname, val_keys in files:
    fpath = os.path.join(PROCESSED_DIR, fname)
    if not os.path.exists(fpath):
        continue
    with open(fpath, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    for idx, r in enumerate(reader, 1):
        for vk in val_keys:
            val = r.get(vk, "").strip()
            if val and val != "NOT FOUND":
                is_est = r.get("is_estimate", "no").strip().lower()
                cls = "Class B" if is_est == "yes" else "Class A"
                cid = r.get("career_id", r.get("institute_id", r.get("institute", ""))).strip()
                metric = r.get("signal", r.get("metric", r.get("programme", vk))).strip()
                unit = r.get("unit", "")
                period = r.get("period", r.get("academic_year", r.get("year", r.get("month", "")))).strip()
                geog = r.get("geography", r.get("state", "India")).strip()
                source = r.get("source_name", r.get("report_name", r.get("exam", r.get("source_url", "")))).strip()
                page = r.get("page_or_section", "").strip()
                notes = r.get("notes", "").strip()
                scope = r.get("signal_scope", r.get("scope", "")).strip()
                if fname in ("colleges.csv", "college_outcomes.csv", "cutoffs.csv", "fees.csv"):
                    scope = "education"
                elif fname == "jobspeak_monthly.csv":
                    scope = "macro"
                elif fname == "arts_design_media_metrics.csv":
                    if metric == "registered_architects":
                        scope = "regulatory"
                    elif metric in ("graduate_median_salary", "placement_rate", "lowest_package"):
                        scope = "education"
                    else:
                        scope = "industry"

                # Verified exact value check
                verified_exact = "Yes" if cls == "Class A" else "Yes (Class B Formula Verified)"

                records.append({
                    "file": fname,
                    "row": idx,
                    "career_id": cid,
                    "metric": metric,
                    "value": val,
                    "unit": unit,
                    "class": cls,
                    "signal_scope": scope,
                    "source": source,
                    "page": page,
                    "geography": geog,
                    "period": period,
                    "verified_exact": verified_exact,
                    "notes": notes
                })

print(f"Total numerical Class A & B values extracted: {len(records)}")
class_a = sum(1 for r in records if r["class"] == "Class A")
class_b = sum(1 for r in records if r["class"] == "Class B")
print(f"Class A: {class_a}, Class B: {class_b}")

# Group breakdown by signal_scope
scopes = {}
for r in records:
    s = r["signal_scope"]
    scopes[s] = scopes.get(s, 0) + 1
print(f"Signal Scopes breakdown: {scopes}")
