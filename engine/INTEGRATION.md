# PRISM Engine — Integration & Answer Mapping Specification

This document defines the interface and exact conversion rules bridging the Udaan student assessment and parent intake answers to the PRISM Engine.

All functions are pure, deterministic, and execute with zero I/O and zero HTTP calls.

---

## 1. Public Facade Function Signatures

All backend consumers must call functions from `engine.public` or `engine.answer_mapping`:

### Answer Mapping (`engine/answer_mapping.py`)
```python
def student_from_answers(
    answers: Dict[str, Any],
    aptitude_correct: Optional[Dict[str, bool]] = None,
    item_to_dimension: Optional[Dict[str, str]] = None,
    stage: str = "school",
    student_id: str = "student",
) -> Student:
    """Pure mapping from student assessment answers dict to Student domain model."""
```

```python
def parent_from_answers(
    answers: Dict[str, Any]
) -> ParentProfile:
    """Pure mapping from parent intake answers dict to ParentProfile domain model."""
```

### Public Facade (`engine/public.py`)
```python
def overall_conflict(
    student: Student,
    parent: ParentProfile
) -> Dict[str, Any]:
    """Compute overall family conflict index (0-100) and 4 stable dimension gaps (0-1)."""
```
**Return structure:**
- `conflict_index`: float in `[0.0, 100.0]`
- `is_high_conflict`: bool (`conflict_index >= 50.0`)
- `dimension_gaps`: `{"risk": float, "domain": float, "relocation": float, "time": float}` in `[0.0, 1.0]`
- `dimension_weights`: `{"risk": 0.25, "domain": 0.25, "relocation": 0.25, "time": 0.25}`
- `family_diagnosis_summary`: English diagnosis text (*Internal/Debug only — NOT for UI display*)
- `dimension_explanations`: Dict of dimension diagnosis text (*Internal/Debug only — NOT for UI display*)

```python
def per_career_scores(
    student: Student,
    parent: ParentProfile,
    careers: Optional[List[StudentCareer]] = None,
    routes: Optional[List[Route]] = None,
    market_records: Optional[List[CareerMarketRecord]] = None,
    student_region: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compute component scores (0-100), conflict, eligibility gates, and data completeness."""
```
**Return item structure:**
- `career_id`: str (snake_case)
- `career_name`: str
- `domain_id`: str (canonical domain ID)
- `student_fit`: float (`F_student` in `[0, 100]`)
- `family_viability`: float (`F_family` in `[0, 100]`)
- `market_score`: float (`F_market` in `[0, 100]`)
- `fit_gap`: float (per-career `|Fit - Family|` gap in `[0, 100]`, Fix 2)
- `career_conflict`: float (alias for backward compatibility)
- `composite_score`: float (blended score in `[0, 100]`, Fix 1: no conflict penalty)
- `g_acad`: int (`1` if passed, `0` if blocked)
- `g_fin`: int (`1` if passed, `0` if blocked)
- `is_viable`: bool (`True` iff `g_acad == 1 and g_fin == 1`)
- `data_complete`: bool (`True` if verified cost, salary, and demand exist)
- `missing_data_fields`: `List[str]` (e.g. `["verified_route_costs"]`)
- `stretch`: bool (`True` if weighted aptitude shortfall exceeds threshold, Fix 3)
- `stretch_reasons`: `List[str]` (specific aptitude shortfalls, Fix 3)
- `data_confidence`: str (`"high"`, `"medium"`, `"low"` based on dropped weight fraction, Fix 4)
- `market_tier`: dict (`demand_tier`, `velocity_tier`, `disruption_tier`, `tier_points`, `confidence`, Fix 5)

```python
def negotiate(
    student: Student,
    parent: ParentProfile,
    alpha: float,
    careers: Optional[List[StudentCareer]] = None,
    routes: Optional[List[Route]] = None,
    market_records: Optional[List[CareerMarketRecord]] = None,
    student_region: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate family negotiation balance slider at position alpha in [0.0, 1.0]."""
```
**Return structure:**
- `alpha`: float (`0.0 = parent priority`, `1.0 = student priority`, `0.5 = balanced`)
- `ranked_careers`: List of dicts (`rank`, `career_id`, `negotiated_score`, `student_fit`, `family_viability`, `fit_gap`, `stretch`, `data_confidence`, `is_in_compromise_zone`, `is_pareto_optimal`)
- `compromise_zone_career_ids`: List of career IDs qualifying in compromise zone (Pareto optimal among `Fit >= 50, Family >= 50`, viable)
- `pareto_optimal_career_ids`: List of non-dominated Pareto career IDs
- `recommended_career_id`: Top compromise career ID, or top ranked career ID
- `balanced_pick_career_id`: Career ID maximizing `min(Fit, Family)` (Fix 8)
- `balanced_pick`: Dict with `career_id`, `student_fit`, `family_viability`, `fit_gap` (Fix 8)

```python
def unified_roadmap(
    student: Student,
    parent: ParentProfile,
    alpha: float = 0.50,
    careers: Optional[List[StudentCareer]] = None,
    routes: Optional[List[Route]] = None,
    market_records: Optional[List[CareerMarketRecord]] = None,
    student_region: Optional[str] = None,
) -> FullRoadmapReport:
    """Generate end-to-end full roadmap with ranked items, blocked reasons, and remedies."""
```

---

## 2. Shared Dimensions Mapping Tables

Every numerical value derived from questionnaire bands is explicitly labeled **assumed**.

### 2.1 Risk Appetite ($R_s, R_p \in [0.0, 1.0]$)
Identical pure function for Student (`pref_risk_1..3`) and Parent (`risk_1..3`):
$$\text{risk} = \frac{\text{number of 'gamble' choices}}{3.0}$$

| Gamble Choices | Safe Choices | Calculated Value | Status |
| :--- | :--- | :--- | :--- |
| 0 | 3 | `0.00` | Exact |
| 1 | 2 | `0.33` | Assumed (1/3 rounded) |
| 2 | 1 | `0.67` | Assumed (2/3 rounded) |
| 3 | 0 | `1.00` | Exact |

### 2.2 Relocation Willingness ($\rho_s, \rho_p \in [0.0, 1.0]$)
Identical for Student (`pref_relocation`) and Parent (`relocation`):

| Question Option ID | Description | Mapped Value | Status |
| :--- | :--- | :--- | :--- |
| `home_city` | Live in home city only | `0.00` | Assumed |
| `same_state` | Anywhere within state | `0.33` | Assumed |
| `anywhere_india` | Anywhere in India | `0.67` | Assumed |
| `abroad_ok` | India or abroad | `1.00` | Assumed |

### 2.3 Maximum Years to First Income ($T_s, T_p$ in Years)
Identical for Student (`pref_time_to_earn`) and Parent (`time_to_earn`):

| Question Option ID | Meaning | Years | Status |
| :--- | :--- | :--- | :--- |
| `within_4y` | Earn within 3 to 4 years | `4.0` | Assumed midpoint/upper |
| `five_six` | Earn within 5 to 6 years | `6.0` | Assumed upper bound |
| `seven_plus` | Willing to wait 7+ years | `8.0` | Assumed representative |

### 2.4 Domain Preferences / Ratings (1-to-5 Scale)
Both Student (`pref_domain_wish`) and Parent (`domain_wish`) accept up to 3 canonical domain IDs.
**Fairness Rule:** Picked = 5.0, Unpicked = 1.0 (an unpicked domain never defaults to neutral 3.0):

| Domain Status | Assigned Rating | Normalized Fit | Status |
| :--- | :--- | :--- | :--- |
| Included in wish list | `5.0` | `1.00` ($=(5-1)/4$) | Assumed priority |
| Not in wish list | `1.0` | `0.00` ($=(1-1)/4$) | Assumed unselected |

---

## 3. Parent Financial Balance Sheet Mapping Tables

### 3.1 Yearly Income Band $\to$ Monthly Household Income ($M_{inc}$)
The engine expects monthly household income in INR ($M_{inc} = \text{yearly} / 12$):

| `income_band` | Annual Range | Assumed Midpoint (Annual) | Monthly $M_{inc}$ (INR) | Status |
| :--- | :--- | :--- | :--- | :--- |
| `under_3l` | ₹0 – ₹3,00,000 | ₹1,50,000 | ₹12,500.00 | Assumed midpoint |
| `3_6l` | ₹3,00,000 – ₹6,00,000 | ₹4,50,000 | ₹37,500.00 | Assumed midpoint |
| `6_12l` | ₹6,00,000 – ₹12,00,000 | ₹9,00,000 | ₹75,000.00 | Assumed midpoint |
| `12_25l` | ₹12,00,000 – ₹25,00,000 | ₹18,50,000 | ₹1,54,166.67 | Assumed midpoint |
| `over_25l` | > ₹25,00,000 | ₹35,00,000 | ₹2,91,666.67 | Assumed (1.4× lower bound) |

### 3.2 Liquid Savings Band ($S$)

| `savings_band` | Range | Assumed Value ($S$) | Status |
| :--- | :--- | :--- | :--- |
| `none` | ₹0 | ₹0.00 | Exact |
| `under_1l` | ₹0 – ₹1,00,000 | ₹50,000.00 | Assumed midpoint |
| `1_3l` | ₹1,00,000 – ₹3,00,000 | ₹2,00,000.00 | Assumed midpoint |
| `3_8l` | ₹3,00,000 – ₹8,00,000 | ₹5,50,000.00 | Assumed midpoint |
| `over_8l` | > ₹8,00,000 | ₹12,00,000.00 | Assumed (1.5× lower bound) |

### 3.3 Maximum Loan Capacity Band ($L_{max}$)

| `loan_band` | Range | Assumed Value ($L_{max}$) | Status |
| :--- | :--- | :--- | :--- |
| `none` | ₹0 | ₹0.00 | Exact |
| `up_to_3l` | ₹0 – ₹3,00,000 | ₹1,50,000.00 | Assumed midpoint |
| `3_8l` | ₹3,00,000 – ₹8,00,000 | ₹5,50,000.00 | Assumed midpoint |
| `8_15l` | ₹8,00,000 – ₹15,00,000 | ₹11,50,000.00 | Assumed midpoint |
| `over_15l` | > ₹15,00,000 | ₹20,00,000.00 | Assumed (1.33× lower bound) |

### 3.4 Monthly Uncommitted Surplus Band ($M$)

| `surplus_band` | Monthly Range | Assumed Value ($M$) | Status |
| :--- | :--- | :--- | :--- |
| `none` | ₹0 | ₹0.00 | Exact |
| `under_5k` | ₹0 – ₹5,000 | ₹2,500.00 | Assumed midpoint |
| `5k_15k` | ₹5,00,000 – ₹15,000 | ₹10,000.00 | Assumed midpoint |
| `15k_30k` | ₹15,000 – ₹30,000 | ₹22,500.00 | Assumed midpoint |
| `over_30k` | > ₹30,000 | ₹45,000.00 | Assumed (1.5× lower bound) |

### 3.5 Monthly Existing EMI Commitments ($E_{exist}$)

| `emi_band` | Monthly Range | Assumed Value ($E_{exist}$) | Status |
| :--- | :--- | :--- | :--- |
| `none` | ₹0 | ₹0.00 | Exact |
| `under_5k` | ₹0 – ₹5,000 | ₹2,500.00 | Assumed midpoint |
| `5k_15k` | ₹5,000 – ₹15,000 | ₹10,000.00 | Assumed midpoint |
| `over_15k` | > ₹15,000 | ₹20,000.00 | Assumed (1.33× lower bound) |

---

## 4. Student Academic & Psychometric Mapping Tables

### 4.1 Academic Stream $\to$ Subject Coverage Set
Mapping guarantees student receives credit for primary subjects without arbitrary penalties:

| `bg_stream` | Covered Subject Tokens in `academics.subjects` |
| :--- | :--- |
| `science_maths` | `{"physics", "chemistry", "mathematics", "english"}` |
| `science_bio` | `{"physics", "chemistry", "biology", "english"}` |
| `commerce` | `{"commerce", "accountancy", "economics", "business_studies", "mathematics", "english"}` |
| `arts` | `{"history", "political_science", "geography", "sociology", "psychology", "english"}` |
| `vocational` | `{"vocational", "applied_arts", "information_technology", "english"}` |
| `undecided` | `{"physics", "chemistry", "mathematics", "biology", "commerce", "accountancy", "economics", "business_studies", "history", "political_science", "geography", "english"}` *(passes all prerequisites)* |

### 4.2 Marks Band to Academic Percentage
**Fairness Rule:** `not_yet` marks mean unknown/unverified, not zero. To uphold the rule that missing data never blocks an aspiration, `not_yet` defaults to `100.0%` so academic minimum cutoffs pass unconditionally.

| `bg_marks_band` | Percentage Range | Assumed Percentage | Status |
| :--- | :--- | :--- | :--- |
| `below_50` | < 50% | `45.0%` | Assumed midpoint [40, 50] |
| `50_60` | 50% – 60% | `55.0%` | Assumed midpoint |
| `60_75` | 60% – 75% | `67.5%` | Assumed midpoint |
| `75_90` | 75% – 90% | `82.5%` | Assumed midpoint |
| `above_90` | 90% – 100% | `95.0%` | Assumed midpoint |
| `not_yet` | Unknown / Awaiting results | `100.0%` | Assumed default (passes cutoffs, unverified) |

### 4.3 RIASEC Interest Items (`int_01` .. `int_12`)
The backend provides the item-to-dimension table (default: 2 items per dimension).
For each dimension $D \in \{R, I, A, S, E, C\}$:
$$\text{item\_normalized} = \frac{\text{raw\_item} - 1.0}{4.0} \in [0.0, 1.0]$$
$$I_s[D] = \text{mean of dimension's normalized items}$$

### 4.4 Aptitude Puzzles
Cognitive traits $\{logical, numerical, verbal, spatial\}$:
- Correct (`True`): `1.0`
- Incorrect (`False`): `0.0`
- Uncollected: `0.50` (assumed neutral)

---

## 5. Uncollected Defaults & Fairness Guarantee

To adhere strictly to the principle **"Never reject an aspiration because of missing or unknown data"**, all attributes not collected in the intake questionnaires are populated with documented, neutral defaults:

| Uncollected Field | Model | Assumed Default | Rationale |
| :--- | :--- | :--- | :--- |
| `min_salary` ($Sal_p$) | `ParentProfile` | ₹3,00,000 / year | Modest baseline; will not disqualify entry-level roles |
| `sector_ratings` | `ParentProfile` | `govt=3, private=3, entrepreneurship=3` | Fully neutral across all sectors |
| `dependents` | `ParentProfile` | `1` | Representative single-student baseline |
| Qualifying Exams | `Student.academics` | `ALL_QUALIFYING_EXAMS_DEFAULT` | Pass-through set (`jee`, `neet`, `cuet`, etc.) ensuring exam gates do not block |
| Skills ($P_k$) | `Student` | `{}` | Empty dict; penalized skill fits are skipped |
| Personality ($P_j$) | `Student` | Neutral `0.50` updated by student `val_*` if present | Neutral baseline |
