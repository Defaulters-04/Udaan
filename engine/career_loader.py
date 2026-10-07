"""Career and Route Data Loader for the PRISM Engine.

Loads and bridges:
1. Seed careers from careers_seed.csv (56 careers across 7 domains).
2. Institutional educational routes and fee structures from data_pipeline/processed/route_costs.csv.
3. Salary bands and entry emoluments from data_pipeline/processed/salary_bands.csv.
4. Detailed humanities, arts, and science profiles from data_pipeline/processed/hss_career_profiles.json.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from engine.parent.models import Route
from engine.student_fit.models import Career as StudentCareer, AcademicRequirement
from engine.domains import normalize_category_to_domain_id

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DATA_PIPELINE_PROCESSED = WORKSPACE_ROOT / "data_pipeline" / "processed"
CONFIG_DIR = WORKSPACE_ROOT / "data_pipeline" / "config"
CAREERS_SEED_FILE = WORKSPACE_ROOT / "careers_seed.csv"


def load_seed_careers_metadata() -> List[Dict[str, str]]:
    """Load metadata for all 56 careers from careers_seed.csv with canonical domain IDs."""
    seed_path = CAREERS_SEED_FILE if CAREERS_SEED_FILE.exists() else (CONFIG_DIR / "careers_seed.csv")
    if not seed_path.exists():
        return []

    careers = []
    with open(seed_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("career_id", "").strip()
            if cid:
                broad_cat = row.get("broad_category", "").strip()
                canonical_domain_id = normalize_category_to_domain_id(broad_cat)
                careers.append({
                    "career_id": cid,
                    "career_name": row.get("career_name", "").strip(),
                    "career_type": row.get("career_type", "").strip(),
                    "broad_category": broad_cat,
                    "subcategory": row.get("subcategory", "").strip(),
                    "domain_id": canonical_domain_id,
                    "domain": canonical_domain_id,
                })
    return careers


def load_route_costs() -> List[Route]:
    """Load verified educational pathways from route_costs.csv into Route models."""
    rc_file = DATA_PIPELINE_PROCESSED / "route_costs.csv"
    if not rc_file.exists():
        return []

    seed_careers = load_seed_careers_metadata()
    career_domain_map = {c["career_id"]: c["domain_id"] for c in seed_careers}

    routes: List[Route] = []
    with open(rc_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("career_id", "").strip()
            rid = row.get("route_id", "").strip()
            if not cid or not rid:
                continue

            try:
                duration = float(row.get("duration_years", 4.0))
            except ValueError:
                duration = 4.0

            try:
                tuition = float(row.get("tuition_fee_total", 0.0))
            except ValueError:
                tuition = 0.0

            try:
                hostel = float(row.get("hostel_fee_total", 0.0)) if row.get("hostel_fee_total") != "NOT FOUND" else 40000.0 * duration
                mess = float(row.get("mess_fee_total", 0.0)) if row.get("mess_fee_total") != "NOT FOUND" else 45000.0 * duration
                living = hostel + mess
            except ValueError:
                living = 85000.0 * duration

            try:
                mandatory = float(row.get("mandatory_fee_total", 0.0)) if row.get("mandatory_fee_total") != "NOT FOUND" else 15000.0
                entrance = float(row.get("entrance_fee", 0.0)) if row.get("entrance_fee") != "NOT FOUND" else 2000.0
                exam_equipment = mandatory + entrance
            except ValueError:
                exam_equipment = 17000.0

            # Sector and canonical domain based on career category
            sector = "private" if any(pvt in row.get("institution_name", "").lower() for pvt in ["vit", "bits", "thapar", "manipal"]) else "govt"
            domain = career_domain_map.get(cid)
            if not domain:
                raw_domain = row.get("domain") or row.get("broad_category") or ""
                domain = normalize_category_to_domain_id(raw_domain) if raw_domain else (
                    "tech_engineering" if "sw" in rid or "aiml" in rid or "ds" in rid else (
                        "healthcare_medicine" if "med" in rid or "bme" in rid else (
                            "design_creative" if "ux" in rid or "id" in rid or "gd" in rid or "fa" in rid else "tech_engineering"
                        )
                    )
                )

            # Starting salary baseline in INR
            starting_salary = 1200000.0 if "iitm" in rid or "iitb" in rid else (
                800000.0 if "vit" in rid or "thapar" in rid or "nitt" in rid else 600000.0
            )

            routes.append(
                Route(
                    career_id=cid,
                    route_id=rid,
                    tuition=tuition,
                    living=living,
                    exam_equipment=exam_equipment,
                    grant=0.0,
                    duration_years=duration,
                    starting_salary=starting_salary,
                    years_to_first_income=duration,
                    career_risk=0.40 if sector == "govt" else 0.55,
                    relocation_need=0.60,
                    domain=domain,
                    sector=sector,
                    g_acad=1,
                )
            )

    return routes


def load_hss_profiles() -> List[Dict[str, Any]]:
    """Load rich humanities, arts, and social sciences profiles from hss_career_profiles.json."""
    hss_file = DATA_PIPELINE_PROCESSED / "hss_career_profiles.json"
    if not hss_file.exists():
        return []

    try:
        with open(hss_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


_COMPLETENESS_CACHE: Optional[Dict[str, tuple[bool, List[str]]]] = None


def get_all_careers_data_completeness() -> Dict[str, tuple[bool, List[str]]]:
    """Audit and cache data completeness for all seed careers across cost, salary, and demand."""
    global _COMPLETENESS_CACHE
    if _COMPLETENESS_CACHE is not None:
        return dict(_COMPLETENESS_CACHE)

    seed_careers = load_seed_careers_metadata()
    rc_file = DATA_PIPELINE_PROCESSED / "route_costs.csv"
    sb_file = DATA_PIPELINE_PROCESSED / "salary_bands.csv"
    dc_file = DATA_PIPELINE_PROCESSED / "demand_coverage.csv"

    cost_complete_ids: Set[str] = set()
    if rc_file.exists():
        try:
            with open(rc_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("cost_status") == "COMPLETE":
                        cost_complete_ids.add(row.get("career_id", "").strip())
        except Exception:
            pass

    salary_complete_ids: Set[str] = set()
    if sb_file.exists():
        try:
            with open(sb_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if (
                        row.get("level") == "entry_level_0_to_2_yr"
                        and row.get("p50") not in ("NOT FOUND", "", None)
                    ):
                        salary_complete_ids.add(row.get("career_id", "").strip())
        except Exception:
            pass

    demand_complete_ids: Set[str] = set()
    if dc_file.exists():
        try:
            with open(dc_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        if int(row.get("signals_found", 0)) > 0:
                            demand_complete_ids.add(row.get("career_id", "").strip())
                    except ValueError:
                        pass
        except Exception:
            pass

    cache: Dict[str, tuple[bool, List[str]]] = {}
    for c in seed_careers:
        cid = c["career_id"]
        missing: List[str] = []
        if cid not in cost_complete_ids:
            missing.append("verified_route_costs")
        if cid not in salary_complete_ids:
            missing.append("verified_entry_salary")
        if cid not in demand_complete_ids:
            missing.append("market_demand_signals")
        cache[cid] = (len(missing) == 0, missing)

    _COMPLETENESS_CACHE = cache
    return dict(cache)


def check_career_data_completeness(career_id: str) -> tuple[bool, List[str]]:
    """Return (data_complete, missing_fields) for a given career_id."""
    audit = get_all_careers_data_completeness()
    if career_id in audit:
        return audit[career_id]
    # For any unknown career, default to incomplete with generic missing tag
    return (False, ["unverified_data"])

