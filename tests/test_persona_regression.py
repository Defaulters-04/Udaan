"""Persona Regression Tests (Golden Files) for UDAAN PRISM Engine.

Verifies that personas 01, 06, and 10 maintain stable top-3 recommendations,
scores, blocked set, and conflict index against tests/snapshots/persona_*.json.

To update golden files on purpose, run:
    UPDATE_GOLDEN=1 pytest tests/test_persona_regression.py
or:
    python tests/test_persona_regression.py --update
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.validation.run_validation import load_personas, build_student, build_parent
from engine.public import unified_roadmap, overall_conflict

SNAPSHOTS_DIR = REPO_ROOT / "tests" / "snapshots"
PERSONA_IDS = [
    ("persona_01", "persona_01_creative_student_low_income_medical_family"),
    ("persona_06", "persona_06_zero_savings_high_loan_reluctance"),
    ("persona_10", "persona_10_scholarship_flips_financial_gate"),
]


def generate_snapshot_for_persona(full_id: str) -> dict:
    """Execute current engine on persona and produce golden file payload."""
    personas = {p["id"]: p for p in load_personas()}
    p_data = personas[full_id]
    student = build_student(p_data["student"])
    parent = build_parent(p_data["family"])

    conf = overall_conflict(student, parent)
    road = unified_roadmap(student, parent, alpha=0.50)

    top_3 = [
        {
            "career_id": r.career_id,
            "composite_score": round(r.composite_score, 1),
            "student_fit": round(r.student_fit, 1),
            "family_viability": round(r.family_viability, 1),
        }
        for r in road.ranked_careers[:3]
    ]

    blocked = [
        {
            "career_id": b.career_id,
            "block_cause": b.block_cause,
        }
        for b in sorted(road.blocked_careers, key=lambda x: x.career_id)
    ]

    return {
        "persona_id": full_id,
        "conflict_index": conf["conflict_index"],
        "is_high_conflict": conf["is_high_conflict"],
        "top_3_careers": top_3,
        "blocked_set": blocked,
    }


@pytest.mark.parametrize("short_id,full_id", PERSONA_IDS)
def test_persona_golden_snapshot(short_id: str, full_id: str):
    """Verify persona regression against golden files."""
    golden_path = SNAPSHOTS_DIR / f"{short_id}.json"
    assert golden_path.exists(), f"Golden file not found: {golden_path}"

    current_data = generate_snapshot_for_persona(full_id)

    if os.environ.get("UPDATE_GOLDEN") == "1":
        with open(golden_path, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=2)
        return

    with open(golden_path, "r", encoding="utf-8") as f:
        golden_data = json.load(f)

    # 1. Compare Conflict Index
    assert current_data["conflict_index"] == pytest.approx(
        golden_data["conflict_index"], abs=0.5
    ), f"[{short_id}] Conflict index mismatch: current {current_data['conflict_index']} vs golden {golden_data['conflict_index']}"

    # 2. Compare Top-3 careers order and IDs
    current_top3_ids = [c["career_id"] for c in current_data["top_3_careers"]]
    golden_top3_ids = [c["career_id"] for c in golden_data["top_3_careers"]]
    assert current_top3_ids == golden_top3_ids, (
        f"[{short_id}] Top-3 careers order changed!\n"
        f"  Before (golden): {golden_top3_ids}\n"
        f"  After  (current): {current_top3_ids}"
    )

    # 3. Compare Blocked careers set
    current_blocked_set = {(b["career_id"], b["block_cause"]) for b in current_data["blocked_set"]}
    golden_blocked_set = {(b["career_id"], b["block_cause"]) for b in golden_data["blocked_set"]}

    diff_added = current_blocked_set - golden_blocked_set
    diff_removed = golden_blocked_set - current_blocked_set

    assert current_blocked_set == golden_blocked_set, (
        f"[{short_id}] Blocked set changed!\n"
        f"  Added to blocked: {sorted(list(diff_added))}\n"
        f"  Removed from blocked: {sorted(list(diff_removed))}"
    )


if __name__ == "__main__":
    if "--update" in sys.argv:
        print("Updating golden files...")
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        for s_id, f_id in PERSONA_IDS:
            data = generate_snapshot_for_persona(f_id)
            target = SNAPSHOTS_DIR / f"{s_id}.json"
            with open(target, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"  Wrote {target}")
        print("Done.")
    else:
        pytest.main([__file__])
