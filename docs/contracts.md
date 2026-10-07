# PRISM Engine Contracts Specification (Post 8 Fixes)

This document specifies the exact data models, JSON payload contracts, and scoring guarantees for the PRISM Engine.

---

## 1. Core Terminology & Nomenclature (Fix 1 & Fix 2)

- **Conflict Index (`conflict_index`):** Strictly and solely refers to the family-level diagnostic divergence between student psychometric aspirations and parent constraints/preferences across the 4 shared dimensions (`risk`, `domain`, `relocation`, `time`). It is diagnostic only (**Fix 1**) and never modifies, scales, or penalizes any score or ranking.
- **Fit Gap (`fit_gap`):** Strictly refers to the per-career divergence between student fit and family viability:
  $$\text{fit\_gap} = |F_{student} - F_{family}|$$
  The field name is `fit_gap` across all code, docs, and JSON responses (**Fix 2**).

---

## 2. Public API & Facade Contracts (`engine.public`)

### 2.1 Overall Family Conflict (`overall_conflict`)
```json
{
  "conflict_index": 37.1,
  "is_high_conflict": false,
  "dimension_gaps": {
    "risk": 0.67,
    "domain": 0.14,
    "relocation": 0.67,
    "time": 0.00
  },
  "dimension_weights": {
    "risk": 0.25,
    "domain": 0.25,
    "relocation": 0.25,
    "time": 0.25
  },
  "family_diagnosis_summary": "Diagnostic text (internal/debug only)",
  "dimension_explanations": {
    "risk": "...",
    "domain": "...",
    "relocation": "...",
    "time": "..."
  }
}
```

### 2.2 Per-Career Evaluation (`per_career_scores`)
Each career in the output list conforms to:
```json
{
  "career_id": "software_engineer",
  "career_name": "Software Engineer",
  "domain_id": "tech_engineering",
  "student_fit": 85.8,
  "family_viability": 71.3,
  "market_score": 75.0,
  "fit_gap": 14.5,
  "career_conflict": 14.5,
  "composite_score": 78.6,
  "g_acad": 1,
  "g_fin": 1,
  "is_viable": true,
  "data_complete": true,
  "missing_data_fields": [],
  "stretch": false,
  "stretch_reasons": [],
  "stretch_shortfall_ratio": 0.0435,
  "data_confidence": "high",
  "financial_status": "normal",
  "market_tier": {
    "demand_tier": "rising",
    "velocity_tier": "stable",
    "disruption_tier": "low",
    "tier_points": 86.0,
    "confidence": "high",
    "evidence_level": "career"
  }
}
```

### 2.3 Negotiation Balance Explorer (`negotiate`)
Evaluates the family negotiation slider at position $\alpha \in [0.0, 1.0]$:
$$\text{negotiated\_score} = \alpha \cdot F_{student} + (1 - \alpha) \cdot F_{family}$$
```json
{
  "alpha": 0.50,
  "ranked_careers": [
    {
      "rank": 1,
      "career_id": "biomedical_engineer",
      "negotiated_score": 82.5,
      "student_fit": 85.8,
      "family_viability": 79.2,
      "fit_gap": 6.6,
      "stretch": false,
      "stretch_reasons": [],
      "data_confidence": "high",
      "is_in_compromise_zone": true,
      "is_pareto_optimal": true
    }
  ],
  "compromise_zone_career_ids": ["biomedical_engineer"],
  "pareto_optimal_career_ids": ["biomedical_engineer"],
  "recommended_career_id": "biomedical_engineer",
  "balanced_pick_career_id": "biomedical_engineer",
  "balanced_pick": {
    "career_id": "biomedical_engineer",
    "student_fit": 85.8,
    "family_viability": 79.2,
    "fit_gap": 6.6
  }
}
```

### 2.4 Blocked Career Contract (`blocked_careers`)
Every blocked career output conforms to:
```json
{
  "career_id": "clinical_doctor",
  "career_name": "Clinical Doctor",
  "block_cause": "academic",
  "failed_gates": ["G_acad"],
  "reasons": ["Academic prerequisites not met (insufficient marks or missing subjects/exams)."],
  "constructive_remedies": ["Focus on qualifying entrance exams or target bridge diploma courses."],
  "cheaper_alternative_routes": [],
  "data_complete": true,
  "missing_data_fields": []
}
```
**`block_cause` Values & Precedence:**
- `"academic"`: Candidate failed academic requirements/marks/subjects gates.
- `"no_route_data"`: No educational routes or cost data exist in the database for this career.
- `"cost"`: Pathways exist but all exceed borrowing capacity or repayment burden limits.
- **Priority when multiple apply:** `academic` > `no_route_data` > `cost`.

---

## 3. Engine Guarantees & Constraints Summary

1. **Conflict Multiplier Elimination (Fix 1):**
   No composite multiplier `(1 - 0.10*conflict/100)` exists. Conflict Index does not modify scores or ranks.
2. **Fit-Family Divergence (Fix 2):**
   `fit_gap = |Fit - Family|`. JSON field `career_conflict` is retained purely as a backward-compatible alias.
3. **Stretch Careers (Fix 3):**
   Calculated by weighted aptitude shortfall ratio:
   $$\frac{\sum u_j \max(0, c_j - a_j)}{\sum u_j c_j} > \text{stretch\_shortfall\_ratio} \ (0.20)$$
   Careers with `stretch = True` are **NOT** blocked and retain their score.
4. **Missing Data Contract (Fix 4):**
   - Inputs/sub-scores that are `None` or `"NOT FOUND"` are dropped, and remaining weights are rescaled to total 1.0. No default substitution.
   - `data_confidence` is `"high"` (dropped weight $\le 0.15$), `"medium"` ($\le 0.35$), or `"low"` ($> 0.35$).
   - If starting salary or route cost is missing, the financial solver returns `status = "insufficient_data"`, setting $F_{family} = 0.0$ and excluding the career from the compromise zone.
5. **Market Tiers (Fix 5):**
   Market scoring maps raw signals directly to absolute tiers (`rising`, `stable`, `declining`; `low`, `medium`, `high` for disruption). Tiers convert to points via lookup table in config. Market is not in composites or slider, serving only as a badge and tiebreaker.
6. **Blended InterestFit (Fix 6):**
   $$InterestFit = 0.50 \cdot 50(1 + r) + 0.50 \cdot 100 \frac{|\text{top3}_s \cap \text{top3}_c|}{3}$$
   Flat student RIASEC vectors ($\text{std} < 0.02$) return $50.0$ with `low_signal = True`.
7. **Explicit Financial Thresholds & Sensitivity (Fix 7):**
   All financial limits (`rb_gate_max`, `dsr_gate_max`, comfort levels, payback horizon/income share) live in config as testable design assumptions. `engine/sensitivity_check.py` validates $\pm 10\%$ perturbations.
8. **2-Score Structure (Fix 8):**
   $$\text{Ranking} = \lambda \cdot F_{student} + (1 - \lambda) \cdot F_{family}$$
   $$\text{Balanced Pick} = \arg\max \min(F_{student}, F_{family})$$
   $$\text{Compromise Zone} = \text{Pareto Frontier}(\{c \in \text{viable} \mid F_{student}(c) \ge 0.50 \land F_{family}(c) \ge 0.50\})$$
9. **Shared Best Route (Fix B1):**
   `negotiate()` and `unified_roadmap()` invoke the identical shared `select_best_feasible_route()` function, ensuring route alignment across the entire PRISM engine.
10. **Unrounded Calculations & Deterministic Tie-Breaking (Fix B2):**
    Intermediate calculations use unrounded raw floats. Output rounding occurs solely at display/JSON serialization. Tie-breaking across rankings, Pareto, and balanced picks strictly follows: **higher score first, then career_id ascending (lexicographical string order)**.
11. **Structured Block Cause (Fix B3):**
    Every blocked career exposes `block_cause: Literal["academic", "no_route_data", "cost"]` with strict precedence (`academic` > `no_route_data` > `cost`).
12. **Explicit Market Defaults (Fix B4):**
    Market scores never hide behind a generic `50.0`. If a career has real signals in `market_signals.csv`, its tier points are evaluated; otherwise, market returns `"NOT FOUND"` with `market_is_default = true` and `confidence = "low"`, ensuring downstream scoring never treats it as numeric.
