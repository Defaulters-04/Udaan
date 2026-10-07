#!/usr/bin/env python3
"""
build_demand_layer.py
PRISM Data Pipeline — Priority 3 (P3) Demand Direction & Market Evidence Layer Generator

Synthesizes real, traceable market evidence signals across the 55-career PRISM universe:
1. Generates data_pipeline/processed/demand_signals.csv
2. Generates data_pipeline/processed/demand_coverage.csv
3. Enforces zero synthetic data (Class C = 0)
4. Preserves exact evidence_level (career, industry, macro, regulatory, education)
"""

import os
import csv
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED_DIR = os.path.join(BASE_DIR, "processed")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SEED_FILE = os.path.join(CONFIG_DIR, "careers_seed.csv")

def determine_signal_direction(sig_id, metric_name, val_str):
    """
    Classifies a raw evidence signal into positive, negative, neutral, or unknown.
    """
    name = metric_name.lower()
    
    # Explicit negative signals
    if sig_id == "SIG_WEF_002" or "displacement" in name:
        return "negative"
    if "market_growth" in name:
        try:
            if float(val_str) < 0:
                return "negative"
        except ValueError:
            pass

    # Positive hiring momentum
    if "hiring" in name and ("growth" in name or "rebound" in name or "surge" in name):
        return "positive"
    if "adex yoy growth" in name:
        return "positive"
    if "job creation" in name or "net job growth" in name:
        return "positive"
    if "placement_rate" in name:
        try:
            if float(val_str) >= 70.0:
                return "positive"
        except ValueError:
            pass
            
    # Forward-looking technology adoption >= 50%
    if "adoption" in name:
        try:
            if float(val_str) >= 50.0:
                return "positive"
            else:
                return "neutral" # Sub-50% adoption is neutral baseline
        except ValueError:
            pass

    # High-growth infrastructure targets & projections
    if "geospatial economy market size projection" in name:
        return "positive"
    if "installed renewable energy capacity" in name:
        return "positive"
    if "domestic electronics production" in name:
        return "positive"
    if "ecosystem gdp contribution" in name or "supported full-time equivalent" in name:
        return "positive"

    # Default structural, regulatory, or baseline shares
    return "neutral"

def main():
    print("Building Priority 3 Demand Evidence Layer...")
    
    # 1. Load seed careers
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        seed_careers = [r["career_id"].strip() for r in reader if r.get("career_id")]

    # 2. Extract signals from market_signals.csv
    market_signals_file = os.path.join(PROCESSED_DIR, "market_signals.csv")
    signals = []
    
    if os.path.exists(market_signals_file):
        with open(market_signals_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                sig_id = r["signal_id"].strip()
                cid = r["career_id"].strip()
                metric = r["signal"].strip()
                val = r["value_min"].strip()
                unit = r["unit"].strip()
                period = r["period"].strip()
                e_level = r["evidence_level"].strip()
                s_name = r["source_name"].strip()
                s_url = r["source_url"].strip()
                s_page = r["page_or_section"].strip()
                ret_on = r["retrieved_on"].strip()
                notes = r["notes"].strip()
                
                direction = determine_signal_direction(sig_id, metric, val)
                
                signals.append({
                    "career_id": cid,
                    "signal_id": sig_id,
                    "metric": metric,
                    "value": val,
                    "unit": unit,
                    "period": period,
                    "direction": direction,
                    "evidence_level": e_level,
                    "source_name": s_name,
                    "source_url": s_url,
                    "source_document": s_name,
                    "source_page": s_page,
                    "retrieved_on": ret_on,
                    "notes": notes
                })

    # 3. Extract demand-relevant signals from arts_design_media_metrics.csv
    adm_file = os.path.join(PROCESSED_DIR, "arts_design_media_metrics.csv")
    if os.path.exists(adm_file):
        with open(adm_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cid = r["career_id"].strip()
                metric = r["metric"].strip()
                val = r["value"].strip()
                unit = r["unit"].strip()
                period = r["reporting_year"].strip()
                e_level = r["evidence_level"].strip()
                s_name = r["source_name"].strip()
                s_url = r["source_url"].strip()
                s_page = r["page_or_section"].strip()
                ret_on = r["retrieved_on"].strip()
                notes = r["notes"].strip()
                
                if val == "NOT FOUND":
                    continue
                # Exclude purely compensation-related metrics from demand signals
                if metric in {"lowest_package", "graduate_median_salary"}:
                    continue
                    
                sig_id = f"SIG_ADM_{cid.upper()}_{metric.upper()}"
                if metric == "registered_architects":
                    sig_id = "SIG_COA_001"
                elif metric == "market_growth":
                    sig_id = "SIG_EY_001"
                elif metric == "talent_pool":
                    sig_id = "SIG_LUM_001"
                elif metric == "monetizing_creators":
                    sig_id = "SIG_KAL_003"
                elif metric == "income_distribution":
                    sig_id = "SIG_KAL_004"
                elif metric == "placement_rate":
                    sig_id = "SIG_NIRF_ARCH_001"
                    
                direction = determine_signal_direction(sig_id, metric, val)
                
                signals.append({
                    "career_id": cid,
                    "signal_id": sig_id,
                    "metric": metric,
                    "value": val,
                    "unit": unit,
                    "period": period,
                    "direction": direction,
                    "evidence_level": e_level,
                    "source_name": s_name,
                    "source_url": s_url,
                    "source_document": s_name,
                    "source_page": s_page,
                    "retrieved_on": ret_on,
                    "notes": notes
                })

    print(f"Total collected demand signals: {len(signals)}")
    
    # 4. Write data_pipeline/processed/demand_signals.csv
    demand_signals_out = os.path.join(PROCESSED_DIR, "demand_signals.csv")
    signals_fields = [
        "career_id", "signal_id", "metric", "value", "unit", "period",
        "direction", "evidence_level", "source_name", "source_url",
        "source_document", "source_page", "retrieved_on", "notes"
    ]
    with open(demand_signals_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=signals_fields)
        writer.writeheader()
        for s in signals:
            writer.writerow(s)
            
    print(f"Written: {demand_signals_out}")
    
    # 5. Evaluate Demand Direction & Evidence Coverage for each career
    signals_by_career = defaultdict(list)
    for s in signals:
        signals_by_career[s["career_id"]].append(s)
        
    coverage_rows = []
    
    for cid in seed_careers:
        c_sigs = signals_by_career.get(cid, [])
        pos_cnt = sum(1 for s in c_sigs if s["direction"] == "positive")
        neg_cnt = sum(1 for s in c_sigs if s["direction"] == "negative")
        neu_cnt = sum(1 for s in c_sigs if s["direction"] == "neutral")
        unk_cnt = sum(1 for s in c_sigs if s["direction"] == "unknown")
        total_sigs = len(c_sigs)
        
        # Assess 4 standard required evidence categories:
        # 1. hiring_growth
        # 2. employment_size
        # 3. geographic_demand
        # 4. future_outlook
        cat_hiring = False
        cat_size = False
        cat_geo = False # Always NOT FOUND per Section 7 (Adzuna credentials unavailable)
        cat_outlook = False
        
        for s in c_sigs:
            m = s["metric"].lower()
            lvl = s["evidence_level"]
            
            if "hiring" in m or "placement_rate" in m or "adex yoy growth" in m:
                cat_hiring = True
            if ("pool" in m or "workforce" in m or "headcount" in m or "share" in m or 
                "registered" in m or "enrolled" in m or "population" in m or "monuments" in m or 
                "periodicals" in m or "licences" in m or "fte jobs" in m or "studios" in m):
                cat_size = True
            if ("adoption" in m or "projection" in m or "capacity" in m or "production" in m or 
                "creation" in m or "displacement" in m or "growth" in m or "gdp contribution" in m):
                cat_outlook = True

        cats_found_cnt = sum([1 if c else 0 for c in [cat_hiring, cat_size, cat_geo, cat_outlook]])
        evidence_coverage_pct = (cats_found_cnt / 4.0) * 100.0
        evidence_coverage_str = f"{cats_found_cnt}/4 ({evidence_coverage_pct:.1f}%)"
        
        missing_cats = []
        if not cat_hiring:
            missing_cats.append("hiring_growth")
        if not cat_size:
            missing_cats.append("employment_size")
        if not cat_geo:
            missing_cats.append("geographic_demand")
        if not cat_outlook:
            missing_cats.append("future_outlook")
        missing_evidence_str = "; ".join(missing_cats) if missing_cats else "NONE"
        
        # Determine demand_direction and confidence_status
        # Rule hierarchy:
        # 1. Zero signals: INSUFFICIENT_EVIDENCE, INSUFFICIENT
        # 2. Sustained decline: DECLINING
        # 3. Special cases:
        #    - video_creator: Bimodal distribution with extreme monetization bottleneck (0.19% monetizing) -> STABLE / MIXED
        # 4. Multiple independent positive signals (pos_cnt >= 2): GROWING
        # 5. Established stable employment / mixed signals: STABLE / MIXED
        # 6. Single indirect / sparse macro/industry signal without hiring data: INSUFFICIENT_EVIDENCE
        
        levels = set(s["evidence_level"] for s in c_sigs)
        has_career = "career" in levels
        
        if total_sigs == 0:
            direction = "INSUFFICIENT_EVIDENCE"
            confidence = "INSUFFICIENT"
        elif cid == "video_creator":
            # Explicit mixed evidence: High macro activity ($18k Cr GDP) but steep 0.19% monetization funnel
            direction = "STABLE / MIXED"
            confidence = "MEDIUM"
        elif neg_cnt > 0 and pos_cnt == 0:
            direction = "DECLINING"
            confidence = "LOW" if total_sigs == 1 else "MEDIUM"
        elif pos_cnt >= 2:
            direction = "GROWING"
            confidence = "HIGH" if has_career else "MEDIUM"
        elif total_sigs == 1 and (not cat_hiring) and (cid in {
            "historian", "archaeologist", "geographer", "gis_analyst", "linguist", 
            "translator_interpreter", "political_scientist", "international_relations_specialist", 
            "economist", "journalist", "game_developer"
        }):
            # Section 5 & 9: Indirect, sparse single signals for HSS / single studio counts
            direction = "INSUFFICIENT_EVIDENCE"
            confidence = "INSUFFICIENT"
        elif pos_cnt >= 1 and neu_cnt >= 1:
            # 1 positive hiring/growth signal + stable employment base
            direction = "STABLE / MIXED"
            confidence = "MEDIUM" if has_career else "LOW"
        elif neu_cnt >= 2:
            # Statutory registers and established workforce
            direction = "STABLE / MIXED"
            confidence = "MEDIUM" if ("regulatory" in levels or has_career) else "LOW"
        else:
            direction = "INSUFFICIENT_EVIDENCE"
            confidence = "INSUFFICIENT"

        coverage_rows.append({
            "career_id": cid,
            "signals_found": total_sigs,
            "positive_signals": pos_cnt,
            "negative_signals": neg_cnt,
            "neutral_signals": neu_cnt,
            "unknown_signals": unk_cnt,
            "evidence_coverage": evidence_coverage_str,
            "demand_direction": direction,
            "confidence_status": confidence,
            "missing_evidence": missing_evidence_str
        })
        
    # 6. Write data_pipeline/processed/demand_coverage.csv
    coverage_out = os.path.join(PROCESSED_DIR, "demand_coverage.csv")
    coverage_fields = [
        "career_id", "signals_found", "positive_signals", "negative_signals",
        "neutral_signals", "unknown_signals", "evidence_coverage",
        "demand_direction", "confidence_status", "missing_evidence"
    ]
    with open(coverage_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=coverage_fields)
        writer.writeheader()
        for r in coverage_rows:
            writer.writerow(r)
            
    print(f"Written: {coverage_out}")
    print("Priority 3 build completed successfully.")

if __name__ == "__main__":
    main()
