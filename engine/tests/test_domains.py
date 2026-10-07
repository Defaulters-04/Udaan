"""Tests for canonical domains taxonomy and career mapping."""

import csv
from pathlib import Path
import pytest

from engine.domains import (
    CANONICAL_DOMAINS,
    get_canonical_domains,
    get_canonical_domain_ids,
    get_canonical_engine_labels,
    get_domain_by_id,
    get_domain_by_engine_label,
    normalize_category_to_domain_id,
    normalize_category_to_engine_label,
)
from engine.career_loader import load_seed_careers_metadata

CAREERS_SEED_FILE = Path(__file__).resolve().parents[2] / "careers_seed.csv"

SEED_CATEGORIES = [
    "Technology & Engineering",
    "Engineering",
    "Healthcare & Medicine",
    "Business & Finance",
    "Management",
    "Business & Marketing",
    "Aviation",
    "Law",
    "Sciences",
    "Design & Creative",
    "Architecture",
    "Media & Entertainment",
    "Creator Economy",
    "Creative & Performing",
    "Creative & Independent",
    "HSS",
]


def test_seven_canonical_domains():
    """Verify there are exactly 7 canonical domains with full metadata."""
    domains = get_canonical_domains()
    assert len(domains) == 7
    ids = get_canonical_domain_ids()
    assert len(ids) == 7
    assert len(set(ids)) == 7  # All unique

    expected_ids = {
        "tech_engineering",
        "business_management",
        "healthcare_medicine",
        "design_creative",
        "media_entertainment",
        "humanities_law",
        "sciences",
    }
    assert set(ids) == expected_ids

    for d in domains:
        assert d.id in expected_ids
        assert d.engine_label
        assert d.en
        assert d.hi
        assert len(d.source_categories) > 0


def test_all_16_seed_categories_map_to_canonical_domains():
    """Every category label listed in requirements maps to exactly one canonical domain."""
    valid_domain_ids = set(get_canonical_domain_ids())

    for cat in SEED_CATEGORIES:
        dom_id = normalize_category_to_domain_id(cat)
        assert dom_id in valid_domain_ids, f"Category '{cat}' mapped to invalid domain '{dom_id}'"

        # Engine label round-trip check
        engine_label = normalize_category_to_engine_label(cat)
        assert engine_label in get_canonical_engine_labels()


def test_every_career_in_seed_csv_maps_to_exactly_one_domain():
    """Every career in careers_seed.csv maps to exactly one canonical domain."""
    assert CAREERS_SEED_FILE.exists(), f"Missing {CAREERS_SEED_FILE}"

    valid_domain_ids = set(get_canonical_domain_ids())
    careers = []
    with open(CAREERS_SEED_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = row.get("career_id", "").strip()
            if cid:
                careers.append(row)

    assert len(careers) >= 55, f"Expected at least 55 careers, got {len(careers)}"

    mapped_domains = set()
    for row in careers:
        cid = row["career_id"]
        broad_cat = row.get("broad_category", "").strip()
        assert broad_cat, f"Career '{cid}' has empty broad_category"

        dom_id = normalize_category_to_domain_id(broad_cat)
        assert dom_id in valid_domain_ids, f"Career '{cid}' category '{broad_cat}' mapped to unknown '{dom_id}'"
        mapped_domains.add(dom_id)

    # Every one of the 7 canonical domains is covered by the careers
    assert mapped_domains == valid_domain_ids, f"Missing coverage for domains: {valid_domain_ids - mapped_domains}"


def test_career_loader_attaches_canonical_domain():
    """Career loader returns metadata with canonical domain_id for every career."""
    seed_careers = load_seed_careers_metadata()
    assert len(seed_careers) >= 55
    valid_domain_ids = set(get_canonical_domain_ids())

    for c in seed_careers:
        assert "domain_id" in c
        assert c["domain_id"] in valid_domain_ids
        assert c["domain"] == c["domain_id"]


def test_domain_lookup_helpers():
    """Verify lookup helpers work by id and engine label."""
    tech = get_domain_by_id("tech_engineering")
    assert tech is not None
    assert tech.engine_label == "Technology & Engineering"
    assert "Engineering" in tech.source_categories

    hss = get_domain_by_engine_label("Humanities, Law & Social Sciences")
    assert hss is not None
    assert hss.id == "humanities_law"

    # Case-insensitive resilience
    assert get_domain_by_id("TECH_ENGINEERING") == tech
    assert normalize_category_to_domain_id("unknown_category_xyz") == "tech_engineering"
