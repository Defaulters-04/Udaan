"""Snapshot data loading and validation for PRISM Market Machine."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import ValidationError

from .models import CareerMarketRecord, RegionalTotals


# Standard snapshot paths
DEFAULT_SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "data" / "snapshots"
DEFAULT_CAREERS_FILE = DEFAULT_SNAPSHOT_DIR / "careers.json"
DEFAULT_DEMO_CAREERS_FILE = DEFAULT_SNAPSHOT_DIR / "demo_careers.json"
DEFAULT_REGIONAL_FILE = DEFAULT_SNAPSHOT_DIR / "regional_totals.json"
DEFAULT_META_FILE = DEFAULT_SNAPSHOT_DIR / "meta.json"


def load_careers_snapshot(file_path: Optional[Path | str] = None) -> List[CareerMarketRecord]:
    """Load and validate careers snapshot from a JSON file.

    Rejects malformed files with a clear error naming the file and field.
    Rejects duplicate career_ids.
    """
    path = Path(file_path) if file_path else DEFAULT_CAREERS_FILE
    if not path.exists():
        # Fall back to demo_careers.json if careers.json does not exist
        if DEFAULT_DEMO_CAREERS_FILE.exists():
            path = DEFAULT_DEMO_CAREERS_FILE
        else:
            raise FileNotFoundError(f"Careers snapshot file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in file '{path.name}': {exc.msg} (line {exc.lineno}, col {exc.colno})") from exc

    if not isinstance(raw_data, list):
        raise ValueError(f"Invalid format in file '{path.name}': expected top-level list of careers, got {type(raw_data).__name__}")

    careers: List[CareerMarketRecord] = []
    seen_ids = set()

    for idx, item in enumerate(raw_data):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid record at index {idx} in file '{path.name}': expected dict, got {type(item).__name__}")

        cid = item.get("career_id")
        if not cid:
            raise ValueError(f"Missing required field 'career_id' at index {idx} in file '{path.name}'")

        if cid in seen_ids:
            raise ValueError(f"Duplicate career_id '{cid}' detected in file '{path.name}' at index {idx}")
        seen_ids.add(cid)

        try:
            record = CareerMarketRecord.model_validate(item)
            careers.append(record)
        except ValidationError as exc:
            first_err = exc.errors()[0]
            field_name = " -> ".join(str(loc) for loc in first_err["loc"])
            err_msg = first_err["msg"]
            raise ValueError(f"Validation error in file '{path.name}' for career '{cid}', field '{field_name}': {err_msg}") from exc

    return careers


def load_regional_totals_snapshot(file_path: Optional[Path | str] = None) -> RegionalTotals:
    """Load and validate regional postings totals snapshot."""
    path = Path(file_path) if file_path else DEFAULT_REGIONAL_FILE
    if not path.exists():
        raise FileNotFoundError(f"Regional totals snapshot file not found at: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in file '{path.name}': {exc.msg}") from exc

    try:
        return RegionalTotals.model_validate(raw_data)
    except ValidationError as exc:
        first_err = exc.errors()[0]
        field_name = " -> ".join(str(loc) for loc in first_err["loc"])
        raise ValueError(f"Validation error in file '{path.name}', field '{field_name}': {first_err['msg']}") from exc


def load_meta_snapshot(file_path: Optional[Path | str] = None) -> Dict[str, Any]:
    """Load snapshot metadata file."""
    path = Path(file_path) if file_path else DEFAULT_META_FILE
    if not path.exists():
        return {"fetched_at": "2026-10-01", "source_labels": {}}

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"fetched_at": "2026-10-01", "source_labels": {}}
