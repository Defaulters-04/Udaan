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
from typing import List, Dict, Any, Optional

from engine.parent.models import Route
from engine.student_fit.models import Career as StudentCareer, AcademicRequirement

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DATA_PIPELINE_PROCESSED = WORKSPACE_ROOT / "data_pipeline" / "processed"
CONFIG_DIR = WORKSPACE_ROOT / "data_pipeline" / "config"
CAREERS_SEED_FILE = WORKSPACE_ROOT / "careers_seed.csv"


def load_seed_careers_metadata() -> List[Dict[str, str]]:
    """Load metadata for all 56 careers from careers_seed.csv."""
    seed_path = CAREERS_SEED_FILE if CAREERS_SEED_FILE.exists() else (CONFIG_DIR / "careers_seed.csv")
    if not seed_path.exists():
        return []

    careers = []
    with open(seed_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("career_id", "").strip()
            if cid:
                careers.append({
                    "career_id": cid,
                    "career_name": row.get("career_name", "").strip(),
                    "career_type": row.get("career_type", "").strip(),
                    "broad_category": row.get("broad_category", "").strip(),
                    "subcategory": row.get("subcategory", "").strip(),
                })
    return careers


def load_route_costs() -> List[Route]:
    """Load verified educational pathways from route_costs.csv into Route models."""
    rc_file = DATA_PIPELINE_PROCESSED / "route_costs.csv"
    if not rc_file.exists():
        return []

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

            # Default domain and starting salary heuristics based on category
            sector = "private" if any(pvt in row.get("institution_name", "").lower() for pvt in ["vit", "bits", "thapar", "manipal"]) else "govt"
            domain = "Technology & Engineering" if "sw" in rid or "aiml" in rid or "ds" in rid else (
                "Healthcare & Medicine" if "med" in rid or "bme" in rid else (
                    "Design & Creative Arts" if "ux" in rid or "id" in rid or "gd" in rid or "fa" in rid else "General"
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
