"""Canonical domain taxonomy and normalisation for the PRISM Engine.

Defines the 7 canonical career domains covering all careers in careers_seed.csv.
Provides mapping between careers_seed categories, canonical IDs, engine labels,
and localized UI display labels.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set


@dataclass(frozen=True)
class DomainInfo:
    """Canonical domain entry specification."""

    id: str  # snake_case identifier (e.g. "tech_engineering")
    engine_label: str  # exact string the engine uses as a domain key
    en: str  # English display label
    hi: str  # Everyday plain Hindi display label
    source_categories: Tuple[str, ...]  # Seed categories absorbed


# The 7 canonical domains covering all 16 seed categories across all 55/56 careers.
CANONICAL_DOMAINS: List[DomainInfo] = [
    DomainInfo(
        id="tech_engineering",
        engine_label="Technology & Engineering",
        en="Technology & Engineering",
        hi="तकनीक और इंजीनियरिंग",
        source_categories=(
            "Technology & Engineering",
            "Engineering",
            "Aviation",
        ),
    ),
    DomainInfo(
        id="business_management",
        engine_label="Business & Management",
        en="Business & Management",
        hi="बिजनेस और मैनेजमेंट",
        source_categories=(
            "Business & Finance",
            "Management",
            "Business & Marketing",
        ),
    ),
    DomainInfo(
        id="healthcare_medicine",
        engine_label="Healthcare & Medicine",
        en="Healthcare & Medicine",
        hi="डॉक्टरी और स्वास्थ्य",
        source_categories=(
            "Healthcare & Medicine",
        ),
    ),
    DomainInfo(
        id="design_creative",
        engine_label="Design & Creative Arts",
        en="Design & Creative Arts",
        hi="डिजाइन और कला",
        source_categories=(
            "Design & Creative",
            "Architecture",
        ),
    ),
    DomainInfo(
        id="media_entertainment",
        engine_label="Media & Entertainment",
        en="Media & Content Creation",
        hi="मीडिया और कंटेंट क्रिएशन",
        source_categories=(
            "Media & Entertainment",
            "Creator Economy",
            "Creative & Performing",
            "Creative & Independent",
        ),
    ),
    DomainInfo(
        id="humanities_law",
        engine_label="Humanities, Law & Social Sciences",
        en="Humanities, Law & Social Sciences",
        hi="कला, कानून और समाज शास्त्र",
        source_categories=(
            "HSS",
            "Law",
        ),
    ),
    DomainInfo(
        id="sciences",
        engine_label="Sciences",
        en="Sciences & Research",
        hi="साइंस और रिसर्च",
        source_categories=(
            "Sciences",
        ),
    ),
]

# Fast lookup mappings
_DOMAIN_BY_ID: Dict[str, DomainInfo] = {d.id: d for d in CANONICAL_DOMAINS}
_DOMAIN_BY_ENGINE_LABEL: Dict[str, DomainInfo] = {d.engine_label.lower(): d for d in CANONICAL_DOMAINS}

# Build normalization map from source categories and various synonyms
_CATEGORY_TO_DOMAIN_MAP: Dict[str, DomainInfo] = {}

for domain in CANONICAL_DOMAINS:
    # Map domain id itself
    _CATEGORY_TO_DOMAIN_MAP[domain.id.lower()] = domain
    # Map engine label
    _CATEGORY_TO_DOMAIN_MAP[domain.engine_label.lower()] = domain
    # Map en label
    _CATEGORY_TO_DOMAIN_MAP[domain.en.lower()] = domain
    # Map all source categories
    for cat in domain.source_categories:
        _CATEGORY_TO_DOMAIN_MAP[cat.lower()] = domain

# Additional aliases / synonyms that might appear in inputs or datasets
_SYNONYM_MAP: Dict[str, str] = {
    "tech": "tech_engineering",
    "technology": "tech_engineering",
    "engineering": "tech_engineering",
    "aviation": "tech_engineering",
    "pilot": "tech_engineering",
    "business": "business_management",
    "finance": "business_management",
    "management": "business_management",
    "marketing": "business_management",
    "healthcare": "healthcare_medicine",
    "medicine": "healthcare_medicine",
    "medical": "healthcare_medicine",
    "health": "healthcare_medicine",
    "design": "design_creative",
    "creative": "design_creative",
    "architecture": "design_creative",
    "arts": "design_creative",
    "media": "media_entertainment",
    "entertainment": "media_entertainment",
    "content": "media_entertainment",
    "creator": "media_entertainment",
    "creator economy": "media_entertainment",
    "performing": "media_entertainment",
    "hss": "humanities_law",
    "humanities": "humanities_law",
    "social sciences": "humanities_law",
    "law": "humanities_law",
    "legal": "humanities_law",
    "science": "sciences",
    "sciences": "sciences",
    "research": "sciences",
}

for syn, target_id in _SYNONYM_MAP.items():
    if target_id in _DOMAIN_BY_ID:
        _CATEGORY_TO_DOMAIN_MAP[syn.lower()] = _DOMAIN_BY_ID[target_id]


def get_canonical_domains() -> List[DomainInfo]:
    """Return all 7 canonical DomainInfo objects."""
    return list(CANONICAL_DOMAINS)


def get_canonical_domain_ids() -> List[str]:
    """Return the list of 7 canonical domain IDs."""
    return [d.id for d in CANONICAL_DOMAINS]


def get_canonical_engine_labels() -> List[str]:
    """Return the list of 7 canonical engine labels."""
    return [d.engine_label for d in CANONICAL_DOMAINS]


def get_domain_by_id(domain_id: str) -> Optional[DomainInfo]:
    """Retrieve DomainInfo by its canonical snake_case id."""
    return _DOMAIN_BY_ID.get(domain_id.strip().lower())


def get_domain_by_engine_label(engine_label: str) -> Optional[DomainInfo]:
    """Retrieve DomainInfo by its engine label."""
    return _DOMAIN_BY_ENGINE_LABEL.get(engine_label.strip().lower())


def normalize_category_to_domain_id(category_or_label: str) -> str:
    """Normalize any raw category, engine label or alias string to its canonical domain id.

    Returns 'tech_engineering' if unrecognized.
    """
    if not category_or_label:
        return "tech_engineering"
    clean = category_or_label.strip().lower()
    entry = _CATEGORY_TO_DOMAIN_MAP.get(clean)
    if entry:
        return entry.id
    # Fallback to general/tech_engineering
    return "tech_engineering"


def normalize_category_to_engine_label(category_or_label: str) -> str:
    """Normalize any raw category, domain id or alias string to its engine label.

    Returns 'Technology & Engineering' if unrecognized.
    """
    domain_id = normalize_category_to_domain_id(category_or_label)
    domain_info = _DOMAIN_BY_ID.get(domain_id)
    if domain_info:
        return domain_info.engine_label
    return "Technology & Engineering"
