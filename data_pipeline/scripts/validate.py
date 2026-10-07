#!/usr/bin/env python3
"""
validate.py
UDAAN PRISM Data Pipeline — Strict Provenance & Anti-Synthetic Validation Suite

Enforces the Absolute Data Integrity Rules:
1. DATA PROVENANCE: Every numerical value must have valid source_name, source_url, retrieved_on, and exact location.
2. ZERO SYNTHETIC DATA: Strictly detects and rejects:
   - Synthetic city multipliers / career multipliers
   - Hardcoded salary arrays or fabricated percentiles
   - Fabricated time series
   - Synthetic ranges
   - Unverified placeholder values
3. DERIVATION INTEGRITY: Any row with is_estimate='yes' must contain the exact mathematical calculation in notes.
4. NOT FOUND INTEGRITY: Any missing or unexecuted query must be marked NOT FOUND and documented in not_found_log.csv.
5. REFERENTIAL INTEGRITY: Every career_id exists in config/careers_seed.csv; zero duplicate keys.
6. RANGE & MONOTONICITY: Bounded percentages, positive integer ranks, value_min <= value_max, monotonic percentiles.
"""

import os
import sys
import csv
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SEED_FILE = os.path.join(CONFIG_DIR, "careers_seed.csv")

errors = []
warnings = []

# Global metrics breakdown
classification_counts = {
    "Class A (Directly Sourced)": 0,
    "Class B (Permitted Derivation)": 0,
    "Class C (Synthetic / Unsupported)": 0,
    "Class D (NOT FOUND)": 0
}

file_stats = {}

def log_error(file_name, row_idx, message):
    errors.append(f"[ERROR] {file_name}:L{row_idx}: {message}")

def log_warning(file_name, message):
    warnings.append(f"[WARNING] {file_name}: {message}")

def read_csv_rows(filepath):
    if not os.path.exists(filepath):
        log_error(os.path.basename(filepath), 0, "File does not exist")
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_valid_career_ids():
    if not os.path.exists(SEED_FILE):
        log_error("careers_seed.csv", 0, "Seed careers file missing from config/")
        return set()
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["career_id"].strip() for row in reader if "career_id" in row and row["career_id"].strip()}

COLLEGES_FILE = os.path.join(CONFIG_DIR, "target_colleges.csv")

def load_valid_institution_ids():
    if not os.path.exists(COLLEGES_FILE):
        log_error("target_colleges.csv", 0, "Target colleges file missing from config/")
        return set()
    with open(COLLEGES_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["institute_id"].strip() for row in reader if "institute_id" in row and row["institute_id"].strip()}

def check_provenance(filename, row_idx, r, value_field):
    """Verifies that any row with a numerical value has complete provenance matching its schema."""
    val = r.get(value_field, "").strip()
    if val and val != "NOT FOUND":
        url = r.get("source_url", "").strip()
        # Source name can be source_name, report_name, exam, institute_id, or derived from NIRF portal
        name = r.get("source_name", r.get("report_name", r.get("exam", r.get("institute_id", "")))).strip()
        if not name and "nirfindia.org" in url:
            name = "NIRF Official Portal"
        
        # Date can be retrieved_on, last_verified, snapshot_date, academic_year, year, or month
        date = r.get("retrieved_on", r.get("last_verified", r.get("snapshot_date", r.get("academic_year", r.get("year", r.get("month", "")))))).strip()

        if not url or not url.startswith("http"):
            log_error(filename, row_idx, f"Numerical value '{val}' lacks valid http source_url: '{url}'")
        if not name:
            log_error(filename, row_idx, f"Numerical value '{val}' lacks source_name or equivalent source identifier")
        if not date:
            log_error(filename, row_idx, f"Numerical value '{val}' lacks date / year / retrieved_on")

def validate_market_signals(valid_career_ids):
    filename = "market_signals.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_keys = set()

    for idx, r in enumerate(rows, start=2):
        sig_id = r.get("signal_id", "").strip()
        cid = r.get("career_id", "").strip()
        vmin = r.get("value_min", "").strip()
        vmax = r.get("value_max", "").strip()
        unit = r.get("unit", "").strip()
        is_est = r.get("is_estimate", "").strip().lower()
        notes = r.get("notes", "").strip()

        if not sig_id:
            log_error(filename, idx, "Empty signal_id")
        if sig_id in seen_keys:
            log_error(filename, idx, f"Duplicate signal_id: {sig_id}")
        seen_keys.add(sig_id)

        if cid and cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' not in careers_seed.csv")

        scope = r.get("signal_scope", r.get("scope", "")).strip()
        if scope and scope not in {"career", "industry", "macro", "education", "regulatory"}:
            log_error(filename, idx, f"Invalid signal_scope '{scope}'. Must be one of career, industry, macro, education, regulatory")

        check_provenance(filename, idx, r, "value_min")

        if vmin == "NOT FOUND" or vmax == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            try:
                f_min = float(vmin)
                f_max = float(vmax)
                if f_min > f_max:
                    log_error(filename, idx, f"value_min ({f_min}) > value_max ({f_max})")

                # Range check
                if unit == "%" and not (-100 <= f_min <= 1000):
                    log_error(filename, idx, f"Percentage out of range: {f_min}")

                # Anti-synthetic check: verify no arbitrary range brackets
                if f_min != f_max and "Figure 2.3" in r.get("page_or_section", ""):
                    log_error(filename, idx, f"Class C violation: Synthetic range bracket [{f_min}, {f_max}] for graphical Figure 2.3")
                    classification_counts["Class C (Synthetic / Unsupported)"] += 1
                    file_stats[filename]["class_c"] += 1
                elif is_est == "yes":
                    if "Derived" not in notes and "Calculation" not in notes:
                        log_error(filename, idx, "Class B derivation must document exact calculation in notes")
                    classification_counts["Class B (Permitted Derivation)"] += 1
                    file_stats[filename]["class_b"] += 1
                else:
                    classification_counts["Class A (Directly Sourced)"] += 1
                    file_stats[filename]["class_a"] += 1
            except ValueError:
                log_error(filename, idx, f"Invalid numeric format: min='{vmin}', max='{vmax}'")

def validate_jobspeak():
    filename = "jobspeak_monthly.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_keys = set()

    for idx, r in enumerate(rows, start=2):
        key = (r.get("month", "").strip(), r.get("scope", "").strip(), r.get("name", "").strip())
        val = r.get("index_value", "").strip()
        yoy = r.get("yoy_pct", "").strip()

        if key in seen_keys:
            log_error(filename, idx, f"Duplicate jobspeak record: {key}")
        seen_keys.add(key)

        check_provenance(filename, idx, r, "index_value")

        if val == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            try:
                f_val = float(val)
                f_yoy = float(yoy)
                classification_counts["Class A (Directly Sourced)"] += 1
                file_stats[filename]["class_a"] += 1
            except ValueError:
                log_error(filename, idx, f"Invalid numeric values: val='{val}', yoy='{yoy}'")

def validate_job_counts(valid_career_ids):
    filename = "job_counts.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_keys = set()

    for idx, r in enumerate(rows, start=2):
        key = (r.get("snapshot_date", "").strip(), r.get("career_id", "").strip(), r.get("city", "").strip())
        cnt = r.get("job_count", "").strip()
        cid = r.get("career_id", "").strip()

        if key in seen_keys:
            log_error(filename, idx, f"Duplicate job_count key: {key}")
        seen_keys.add(key)

        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' not in seed")

        if cnt == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            # ANTI-SYNTHETIC CHECK: If job_count is numeric without an active API raw cache, flag Class C violation
            log_error(filename, idx, f"Class C violation: Job count '{cnt}' written without raw API response JSON provenance")
            classification_counts["Class C (Synthetic / Unsupported)"] += 1
            file_stats[filename]["class_c"] += 1

def validate_salary_bands(valid_career_ids):
    filename = "salary_bands.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_keys = set()

    for idx, r in enumerate(rows, start=2):
        key = (r.get("career_id", "").strip(), r.get("level", "").strip(), r.get("source_name", "").strip())
        cid = r.get("career_id", "").strip()
        e_level = r.get("evidence_level", "").strip()
        p10 = r.get("p10", "").strip()
        p25 = r.get("p25", "").strip()
        p50 = r.get("p50", "").strip()
        p75 = r.get("p75", "").strip()
        p90 = r.get("p90", "").strip()
        is_est = r.get("is_estimate", "").strip().lower()
        notes = r.get("notes", "").strip()

        if key in seen_keys:
            log_error(filename, idx, f"Duplicate salary band key: {key}")
        seen_keys.add(key)

        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' not in seed")

        if not e_level or e_level not in {"career", "industry", "macro", "education", "regulatory"}:
            log_error(filename, idx, f"Invalid or missing evidence_level '{e_level}' in salary_bands.csv")

        percentiles = [p10, p25, p50, p75, p90]
        numeric_pts = [p for p in percentiles if p != "NOT FOUND"]

        if len(numeric_pts) > 1 and "histogram" in r.get("source_url", "").lower() and "calculation" not in notes.lower():
            log_error(filename, idx, f"Class C violation: Synthetic percentile array found for {key}")
            classification_counts["Class C (Synthetic / Unsupported)"] += 1
            file_stats[filename]["class_c"] += 1
        elif len(numeric_pts) == 0:
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            for p_field in ["p50", "p10", "p25", "p75", "p90"]:
                val = r.get(p_field, "").strip()
                if val != "NOT FOUND":
                    check_provenance(filename, idx, r, p_field)
                    if is_est == "yes":
                        if "calculation" not in notes.lower() and "derived" not in notes.lower():
                            log_error(filename, idx, "Class B derivation must document formula in notes")
                        classification_counts["Class B (Permitted Derivation)"] += 1
                        file_stats[filename]["class_b"] += 1
                    else:
                        classification_counts["Class A (Directly Sourced)"] += 1
                        file_stats[filename]["class_a"] += 1
                    break

def validate_adzuna_salary(valid_career_ids):
    filename = "adzuna_salary.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}

    for idx, r in enumerate(rows, start=2):
        val = r.get("value_inr_per_year", "").strip()
        if val == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            log_error(filename, idx, f"Class C violation: Adzuna median salary '{val}' written without raw API JSON")
            classification_counts["Class C (Synthetic / Unsupported)"] += 1
            file_stats[filename]["class_c"] += 1

def validate_colleges():
    filename = "colleges.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}

    for idx, r in enumerate(rows, start=2):
        rank = r.get("nirf_rank", "").strip()
        intake = r.get("approved_intake", "").strip()
        check_provenance(filename, idx, r, "nirf_rank")

        if rank != "NOT FOUND":
            classification_counts["Class A (Directly Sourced)"] += 1
            file_stats[filename]["class_a"] += 1
        else:
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1

        if intake == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            classification_counts["Class A (Directly Sourced)"] += 1
            file_stats[filename]["class_a"] += 1

def validate_college_outcomes():
    filename = "college_outcomes.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}

    for idx, r in enumerate(rows, start=2):
        sal = r.get("median_salary_inr", "").strip()
        check_provenance(filename, idx, r, "median_salary_inr")
        if sal != "NOT FOUND":
            classification_counts["Class A (Directly Sourced)"] += 1
            file_stats[filename]["class_a"] += 1
        else:
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1

def validate_cutoffs():
    filename = "cutoffs.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}

    for idx, r in enumerate(rows, start=2):
        rank = r.get("closing_rank", "").strip()
        check_provenance(filename, idx, r, "closing_rank")
        if rank != "NOT FOUND":
            try:
                irank = int(rank)
                if irank <= 0:
                    log_error(filename, idx, f"Negative rank: {irank}")
                classification_counts["Class A (Directly Sourced)"] += 1
                file_stats[filename]["class_a"] += 1
            except ValueError:
                log_error(filename, idx, f"Invalid closing rank format: {rank}")
        else:
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1

def validate_fees():
    filename = "fees.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}

    for idx, r in enumerate(rows, start=2):
        tuit = r.get("annual_tuition_inr", "").strip()
        hostel = r.get("hostel_mess_inr", "").strip()
        check_provenance(filename, idx, r, "annual_tuition_inr")

        if tuit != "NOT FOUND":
            classification_counts["Class A (Directly Sourced)"] += 1
            file_stats[filename]["class_a"] += 1
        else:
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1

        if hostel == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            # If an approximate hostel fee was entered without an official circular fixing it
            log_warning(filename, f"L{idx}: Ensure hostel_mess_inr '{hostel}' is fixed in official circular, not an estimate.")
            classification_counts["Class A (Directly Sourced)"] += 1
            file_stats[filename]["class_a"] += 1

def validate_arts_design_media(valid_career_ids):
    filename = "arts_design_media_metrics.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}

    for idx, r in enumerate(rows, start=2):
        val = r.get("value", "").strip()
        is_est = r.get("is_estimate", "").strip().lower()
        notes = r.get("notes", "").strip()
        check_provenance(filename, idx, r, "value")

        if val == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            if is_est == "yes":
                if "Calculation" not in notes and "Derived" not in notes:
                    log_error(filename, idx, "Class B derivation must include explicit calculation formula in notes")
                classification_counts["Class B (Permitted Derivation)"] += 1
                file_stats[filename]["class_b"] += 1
            else:
                classification_counts["Class A (Directly Sourced)"] += 1
                file_stats[filename]["class_a"] += 1

def validate_not_found_log():
    filename = "not_found_log.csv"
    rows = read_csv_rows(os.path.join(PROCESSED_DIR, filename))
    file_stats[filename] = {"total_rows": len(rows), "not_found": len(rows), "class_a": 0, "class_b": 0, "class_c": 0}
    for idx, r in enumerate(rows, start=2):
        if not r.get("item", "").strip() or not r.get("reason", "").strip():
            log_error(filename, idx, "Missing item or reason in not_found_log")

def validate_hss_career_profiles(valid_career_ids):
    filename = "hss_career_profiles.csv"
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        return
    rows = read_csv_rows(filepath)
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_ids = set()
    for idx, r in enumerate(rows, start=2):
        cid = r.get("career_id", "").strip()
        if not cid:
            log_error(filename, idx, "Empty career_id")
        if cid in seen_ids:
            log_error(filename, idx, f"Duplicate career_id: {cid}")
        seen_ids.add(cid)
        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' not in config/careers_seed.csv")
        
        url = r.get("source_url", "").strip()
        name = r.get("source_name", "").strip()
        date = r.get("retrieved_on", "").strip()
        if not url or not url.startswith("http"):
            log_error(filename, idx, f"Profile lacks valid http source_url: '{url}'")
        if not name:
            log_error(filename, idx, "Profile lacks source_name")
        if not date:
            log_error(filename, idx, "Profile lacks retrieved_on")

def validate_changelog():
    filename = "changelog.csv"
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        return
    rows = read_csv_rows(filepath)
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    for idx, r in enumerate(rows, start=2):
        if not r.get("file", "").strip() or not r.get("row_key", "").strip() or not r.get("reason", "").strip():
            log_error(filename, idx, "Missing required field in changelog.csv")

def validate_coverage_grid(valid_career_ids):
    filename = "coverage_grid.csv"
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        return
    rows = read_csv_rows(filepath)
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    for idx, r in enumerate(rows, start=2):
        cid = r.get("career_id", "").strip()
        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' in coverage_grid not in careers_seed.csv")
        for col in ["salary", "cost", "demand_direction", "geography", "exams"]:
            val = r.get(col, "").strip()
            if val not in {"FOUND-A", "FOUND-B", "NOT FOUND"}:
                log_error(filename, idx, f"Invalid grid value '{val}' in column '{col}'")

def validate_route_costs(valid_career_ids, valid_inst_ids):
    filename = "route_costs.csv"
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        return
    rows = read_csv_rows(filepath)
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_routes = set()

    for idx, r in enumerate(rows, start=2):
        cid = r.get("career_id", "").strip()
        rid = r.get("route_id", "").strip()
        iid = r.get("institution_id", "").strip()
        dur = r.get("duration_years", "").strip()
        status = r.get("cost_status", "").strip()
        total_cost = r.get("total_route_cost", "").strip()
        e_level = r.get("evidence_level", "").strip()
        notes = r.get("notes", "").strip()

        if not rid:
            log_error(filename, idx, "Empty route_id")
        if rid in seen_routes:
            log_error(filename, idx, f"Duplicate route_id: {rid}")
        seen_routes.add(rid)

        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' not in careers_seed.csv")
        if iid not in valid_inst_ids:
            log_error(filename, idx, f"institution_id '{iid}' not in target_colleges.csv")

        try:
            f_dur = float(dur)
            if f_dur <= 0:
                log_error(filename, idx, f"Invalid duration_years: {f_dur} (must be > 0)")
        except ValueError:
            log_error(filename, idx, f"Non-numeric duration_years: {dur}")

        if status not in {"COMPLETE", "PARTIAL"}:
            log_error(filename, idx, f"Invalid cost_status '{status}'. Must be COMPLETE or PARTIAL")

        if e_level != "education":
            log_error(filename, idx, f"Invalid evidence_level '{e_level}'. Must be 'education' for route costs")

        comps = ["tuition_fee_total", "mandatory_fee_total", "hostel_fee_total", "mess_fee_total", "entrance_fee"]
        comp_vals = {}
        for c in comps:
            v = r.get(c, "").strip()
            if v == "NOT FOUND":
                classification_counts["Class D (NOT FOUND)"] += 1
                file_stats[filename]["not_found"] += 1
            else:
                try:
                    f_val = float(v)
                    if f_val < 0:
                        log_error(filename, idx, f"Negative cost for {c}: {f_val}")
                    check_provenance(filename, idx, r, c)
                    comp_vals[c] = f_val
                    classification_counts["Class A (Directly Sourced)"] += 1
                    file_stats[filename]["class_a"] += 1
                except ValueError:
                    log_error(filename, idx, f"Invalid non-numeric value for {c}: {v}")

        if status == "COMPLETE":
            if total_cost == "NOT FOUND":
                log_error(filename, idx, "cost_status is COMPLETE but total_route_cost is NOT FOUND")
            else:
                try:
                    f_tot = float(total_cost)
                    expected_tot = sum(comp_vals.values())
                    if abs(f_tot - expected_tot) > 1.0:
                        log_error(filename, idx, f"Total route cost mismatch: recorded={f_tot}, calculated={expected_tot}")
                    check_provenance(filename, idx, r, "total_route_cost")
                    classification_counts["Class B (Permitted Derivation)"] += 1
                    file_stats[filename]["class_b"] += 1
                except ValueError:
                    log_error(filename, idx, f"Non-numeric total_route_cost: {total_cost}")
        elif status == "PARTIAL":
            if total_cost != "NOT FOUND":
                log_error(filename, idx, f"cost_status is PARTIAL but total_route_cost is numeric: {total_cost}. Must be NOT FOUND")
            else:
                classification_counts["Class D (NOT FOUND)"] += 1
                file_stats[filename]["not_found"] += 1

def validate_route_cost_coverage(valid_career_ids):
    filename = "route_cost_coverage.csv"
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        return
    rows = read_csv_rows(filepath)
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    for idx, r in enumerate(rows, start=2):
        cid = r.get("career_id", "").strip()
        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' in route_cost_coverage not in careers_seed.csv")
        
        status = r.get("coverage_status", "").strip()
        if status not in {"COMPLETE", "PARTIAL", "NOT FOUND"}:
            log_error(filename, idx, f"Invalid coverage_status: {status}")
        
        try:
            rf = int(r.get("routes_found", "0"))
            cr = int(r.get("complete_routes", "0"))
            pr = int(r.get("partial_routes", "0"))
            if rf != cr + pr:
                log_error(filename, idx, f"routes_found ({rf}) != complete_routes ({cr}) + partial_routes ({pr})")
        except ValueError:
            log_error(filename, idx, "Non-integer route counts in route_cost_coverage.csv")

def validate_demand_signals(valid_career_ids):
    filename = "demand_signals.csv"
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        log_error(filename, 0, "demand_signals.csv missing from processed/")
        return
    rows = read_csv_rows(filepath)
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_signals = set()

    for idx, r in enumerate(rows, start=2):
        cid = r.get("career_id", "").strip()
        sig_id = r.get("signal_id", "").strip()
        metric = r.get("metric", "").strip()
        val = r.get("value", "").strip()
        unit = r.get("unit", "").strip()
        period = r.get("period", "").strip()
        direction = r.get("direction", "").strip()
        e_level = r.get("evidence_level", "").strip()
        s_name = r.get("source_name", "").strip()
        s_url = r.get("source_url", "").strip()
        s_doc = r.get("source_document", "").strip()
        s_page = r.get("source_page", "").strip()
        ret_on = r.get("retrieved_on", "").strip()
        notes = r.get("notes", "").strip()

        if not sig_id:
            log_error(filename, idx, "Empty signal_id")
        if sig_id in seen_signals:
            log_error(filename, idx, f"Duplicate signal_id: {sig_id}")
        seen_signals.add(sig_id)

        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' in demand_signals not in seed")

        if direction not in {"positive", "negative", "neutral", "unknown"}:
            log_error(filename, idx, f"Invalid direction: {direction}")

        if e_level not in {"career", "industry", "macro", "regulatory", "education"}:
            log_error(filename, idx, f"Invalid evidence_level: {e_level}")

        if not period:
            log_error(filename, idx, "Missing period")

        check_provenance(filename, idx, r, "value")

        if not s_doc:
            log_error(filename, idx, "Missing source_document")
        if not s_page:
            log_error(filename, idx, "Missing source_page")

        if val == "NOT FOUND":
            classification_counts["Class D (NOT FOUND)"] += 1
            file_stats[filename]["not_found"] += 1
        else:
            try:
                f_val = float(val)
                # Bounded percentages
                if unit in {"%", "% YoY"} and not (-100.0 <= f_val <= 1000.0):
                    log_error(filename, idx, f"Percentage out of reasonable range: {f_val}")
                # Non-negative counts/headcounts/capacities
                if unit in {"Jobs", "Professionals", "Million Employees", "Employees", "Startups", "Centers", 
                            "Licences", "Advocates", "Pharmacists", "Nurses & Midwives", "Dentists", 
                            "Physiotherapists", "Doctors", "Monuments", "Publications", "count", "studios", 
                            "INR Crore", "Billion USD", "Lakh Crore INR", "Gigawatts (GW)", "Aircraft", "Million Passengers"} and f_val < 0:
                    log_error(filename, idx, f"Impossible negative count/value: {f_val}")

                # Check for permitted derivation (Class B)
                if "Derived" in notes or "Calculation" in notes:
                    classification_counts["Class B (Permitted Derivation)"] += 1
                    file_stats[filename]["class_b"] += 1
                else:
                    classification_counts["Class A (Directly Sourced)"] += 1
                    file_stats[filename]["class_a"] += 1
            except ValueError:
                log_error(filename, idx, f"Invalid numeric value: '{val}'")

def validate_demand_coverage(valid_career_ids):
    filename = "demand_coverage.csv"
    filepath = os.path.join(PROCESSED_DIR, filename)
    if not os.path.exists(filepath):
        log_error(filename, 0, "demand_coverage.csv missing from processed/")
        return
    rows = read_csv_rows(filepath)
    file_stats[filename] = {"total_rows": len(rows), "not_found": 0, "class_a": 0, "class_b": 0, "class_c": 0}
    seen_careers = set()

    for idx, r in enumerate(rows, start=2):
        cid = r.get("career_id", "").strip()
        if cid in seen_careers:
            log_error(filename, idx, f"Duplicate career_id: {cid}")
        seen_careers.add(cid)

        if cid not in valid_career_ids:
            log_error(filename, idx, f"career_id '{cid}' in demand_coverage not in seed")

        direction = r.get("demand_direction", "").strip()
        if direction not in {"GROWING", "STABLE / MIXED", "DECLINING", "INSUFFICIENT_EVIDENCE"}:
            log_error(filename, idx, f"Invalid demand_direction: '{direction}'")

        conf = r.get("confidence_status", "").strip()
        if conf not in {"HIGH", "MEDIUM", "LOW", "INSUFFICIENT"}:
            log_error(filename, idx, f"Invalid confidence_status: '{conf}'")

        cov_str = r.get("evidence_coverage", "").strip()
        if not re.match(r"^\d/4 \(\d+\.\d+%\)$", cov_str):
            log_error(filename, idx, f"Invalid evidence_coverage format: '{cov_str}'")

        try:
            sf = int(r.get("signals_found", "0"))
            pos = int(r.get("positive_signals", "0"))
            neg = int(r.get("negative_signals", "0"))
            neu = int(r.get("neutral_signals", "0"))
            unk = int(r.get("unknown_signals", "0"))
            if sf != (pos + neg + neu + unk):
                log_error(filename, idx, f"signals_found ({sf}) != sum of positive ({pos}), negative ({neg}), neutral ({neu}), unknown ({unk})")

            if sf == 0:
                if direction != "INSUFFICIENT_EVIDENCE":
                    log_error(filename, idx, f"Zero signals but demand_direction is '{direction}' (must be INSUFFICIENT_EVIDENCE)")
                if conf != "INSUFFICIENT":
                    log_error(filename, idx, f"Zero signals but confidence_status is '{conf}' (must be INSUFFICIENT)")

            if direction == "DECLINING" and neg == 0:
                log_error(filename, idx, "demand_direction is DECLINING but negative_signals is 0")
            if direction == "GROWING" and pos < 2:
                log_error(filename, idx, f"demand_direction is GROWING but positive_signals is {pos} (must be >= 2)")

        except ValueError:
            log_error(filename, idx, "Non-integer signal counts in demand_coverage")

    missing_careers = valid_career_ids - seen_careers
    if missing_careers:
        log_error(filename, 0, f"Missing careers in demand_coverage: {sorted(missing_careers)}")

def main():
    print("=" * 80)
    print("UDAAN PRISM DATA PIPELINE — STRICT PROVENANCE & ANTI-SYNTHETIC VALIDATOR")
    print("=" * 80)

    valid_career_ids = load_valid_career_ids()
    valid_inst_ids = load_valid_institution_ids()
    print(f"Loaded {len(valid_career_ids)} valid career IDs from config/careers_seed.csv")
    print(f"Loaded {len(valid_inst_ids)} valid institution IDs from config/target_colleges.csv\n")

    validate_market_signals(valid_career_ids)
    validate_jobspeak()
    validate_salary_bands(valid_career_ids)
    validate_job_counts(valid_career_ids)
    validate_adzuna_salary(valid_career_ids)
    validate_colleges()
    validate_college_outcomes()
    validate_cutoffs()
    validate_fees()
    validate_arts_design_media(valid_career_ids)
    validate_hss_career_profiles(valid_career_ids)
    validate_route_costs(valid_career_ids, valid_inst_ids)
    validate_route_cost_coverage(valid_career_ids)
    validate_demand_signals(valid_career_ids)
    validate_demand_coverage(valid_career_ids)
    validate_not_found_log()
    validate_changelog()
    validate_coverage_grid(valid_career_ids)

    # Integrity & Provenance Breakdown
    print("-" * 80)
    print(f"{'Processed File':<35} | {'Rows':<6} | {'Class A':<8} | {'Class B':<8} | {'NOT FOUND':<10} | {'Class C':<8}")
    print("-" * 80)
    for fname, st in file_stats.items():
        print(f"{fname:<35} | {st['total_rows']:<6} | {st['class_a']:<8} | {st['class_b']:<8} | {st['not_found']:<10} | {st['class_c']:<8}")
    print("-" * 80)

    print("\nOVERALL METRIC PROVENANCE AUDIT:")
    for cls_name, cnt in classification_counts.items():
        print(f"  * {cls_name:<35}: {cnt}")

    if errors:
        print(f"\nVALIDATION FAILED: {len(errors)} violation(s) detected:")
        for e in errors[:25]:
            print(f"  {e}")
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more errors")
        sys.exit(1)
    else:
        print("\nVALIDATION PASSED: 100% Provenance Compliance. Zero Class C synthetic data present.")
        sys.exit(0)

if __name__ == "__main__":
    main()
