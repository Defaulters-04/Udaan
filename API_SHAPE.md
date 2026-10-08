# PRISM Engine API Shape Specification (DataQuest 3.0)

> **Notice to Backend Owner**:
> This document defines the exact engine output contract produced by `evaluate_family(...)`.
> Per engine specification guidelines, `API_CONTRACT.md` has NOT been edited or overwritten.
> The backend owner should review and align `API_CONTRACT.md` and downstream API endpoints with the schema documented below.

---

## 1. Top-Level Response Structure

```typescript
interface FamilyEvaluationResponse {
  engine_version: string;             // e.g. "PRISM-2.0"
  scale_used: "0-100";                // Standardized 0-100 scale
  conflict_index: number;             // Composite parental/student alignment conflict (0-100)
  dimension_gaps: {
    risk: number;
    domain: number;
    relocation: number;
    time: number;
  };
  dimension_breakdown: {
    [dimension: string]: {
      gap: number;
      weight: number;
    };
  };
  high_conflict: boolean;             // True if conflict_index > high_conflict_threshold
  high_conflict_threshold: number;   // Configurable threshold (default: 60.0)
  careers: CareerEvaluationReport[];  // Ranked list of all 55 careers
  warnings: string[];
}
```

---

## 2. Career Evaluation Schema (`CareerEvaluationReport`)

Every career entry in `careers` contains:
- **`career_id`**: String identifier (e.g. `"ux_designer"`).
- **`career_name`**: Human-readable name.
- **`domain`**: Domain identifier (e.g. `"design_creative"`, `"tech_engineering"`).
- **`data_status`**: `"core"` (one of the 18 benchmark core careers) or `"pending"` (retained in catalog, excluded from ranking with explicit reason).
- **`pending_reason`**: `null` for core careers; explicit explanation string for pending careers.
- **`best_route`**: Financial/academic route selected as optimal. **Crucial rule**: this exact same route is used for ALL metrics: cost, EMI, payback, gates, and scores.
- **`alternative_routes`**: List of other evaluated routes for this career.
- **`cost`**:
  - `total`: Total 4-year / program cost (including tuition, hostel, mess, exam/equipment). `null` if any mandatory item is missing.
  - `total_cost_known`: Computed known cost (lower bound).
  - `cost_status`: `"complete"` | `"partial"` | `"missing"`.
  - `missing_fields`: Array of missing cost attributes (e.g. `["hostel", "mess"]`).
  - `is_lower_bound`: Boolean, `true` when non-tuition costs are absent.
- **`scores`**:
  - `fit`: Student dimensional fit score (0-100).
  - `family_viability`: Financial & parental preference score (0-100, `null` if unscoreable).
  - `market`: Market demand score (`null` if no verified signal).
  - `composite`: Blended fit/family score (`null` if blocked or pending).
  - `final`: Final decision score.
- **`gates`**:
  - `gate_financial`: `1` (cleared), `0` (failed), or `null`.
  - `gate_academic`: `1` (eligible), `0` (ineligible), or `null`.
  - `provisional_pass`: `true` if lower-bound passed financial gate with missing auxiliary costs. Never shown as confirmed pass.
- **`blocked`**: Boolean flag.
- **`blocked_cause`**: Fixed engine enum (`"loan_exceeds_cap"` | `"household_emi_too_high"` | `"graduate_dsr_too_high"` | `"academic_ineligible"` | `"not_enough_data"` | `null`).
- **`funding_gap`**: Float deficit amount or `null`.
- **`shortfall_details`**: Breakdown containing `grant_needed`, `loan_needed`, `loan_max`, `monthly_emi`, or `null`.
- **`remedies`**: List of actionable recommendations `{cause, text_en, text_hi, action}` in everyday English and natural conversational Hindi.
- **`blend_grid`**: Exactly 21 entries for $\lambda \in [0.00, 0.05, \dots, 1.00]$, where `rank_score = lambda * fit + (1 - lambda) * family_viability`. Frontend never needs to calculate blends or ranks.
- **`pareto`**: Boolean, indicates whether career is on the Pareto frontier (compromise zone).
- **`balanced_pick`**: Boolean, maximizes $\min(\text{Fit}, \text{Family})$.
- **`sources`**: List of provenance records `{field, source_url, retrieved_on}`.
- **`stability_top3`**: Float in `[0, 1]` representing Monte Carlo sensitivity stability, or `null`.

---

## 3. Concrete Example Payloads

### Example 1: Complete Career (`ux_designer`)
All required and living cost fields verified. `cost_status = "complete"`. Confirmed gate pass.

```json
{
  "career_id": "ux_designer",
  "career_name": "UX/UI Designer",
  "domain": "design_creative",
  "data_status": "core",
  "pending_reason": null,
  "best_route": {
    "route_id": "route_ux_iitb",
    "institution_name": "Indian Institute of Technology Bombay",
    "program_name": "B.Des (Bachelor of Design, IDC)",
    "duration_years": 4.0,
    "net_cost": 1107600.0,
    "loan_needed": 497600.0,
    "monthly_emi": 8260.75,
    "repayment_burden": 0.1326,
    "debt_service_ratio": 0.0536,
    "payback_years": 2.99,
    "cost_status": "complete",
    "is_lower_bound": false,
    "provisional_pass": false
  },
  "alternative_routes": [
    {
      "route_id": "route_ux_nid",
      "institution_name": "National Institute of Design Ahmedabad",
      "program_name": "B.Des (Interaction Design)",
      "net_cost": 1951000.0,
      "f_family": 0.0,
      "gate_cleared": 0,
      "cost_status": "partial"
    }
  ],
  "cost": {
    "total": 1107600.0,
    "total_cost_known": 1107600.0,
    "cost_status": "complete",
    "missing_fields": [],
    "is_lower_bound": false
  },
  "scores": {
    "fit": 79.97,
    "family_viability": 81.78,
    "market": null,
    "composite": 80.88,
    "final": 80.88
  },
  "gates": {
    "gate_financial": 1,
    "gate_academic": 1,
    "provisional_pass": false
  },
  "blocked": false,
  "blocked_cause": null,
  "funding_gap": null,
  "shortfall_details": null,
  "remedies": [],
  "blend_grid": [
    {"lambda": 0.0, "rank_score": 81.78, "rank": 12},
    {"lambda": 0.05, "rank_score": 81.69, "rank": 12},
    {"lambda": 0.5, "rank_score": 80.88, "rank": 10},
    {"lambda": 0.95, "rank_score": 80.06, "rank": 8},
    {"lambda": 1.0, "rank_score": 79.97, "rank": 8}
  ],
  "pareto": false,
  "balanced_pick": false,
  "sources": [
    {
      "field": "starting_salary",
      "source_url": "https://www.nirfindia.org/2024/Declaration/Agreement/DCS/IR-O-U-0306.pdf",
      "retrieved_on": "2026-10-07"
    },
    {
      "field": "route_route_ux_iitb_fee",
      "source_url": "https://www.iitb.ac.in/newacadhome/toFeeStructure.jsp",
      "retrieved_on": "2026-10-07"
    }
  ],
  "stability_top3": 0.0
}
```

---

### Example 2: Partial Career (`software_developer`)
Tuition and duration verified; hostel/mess absent from official source. Evaluated on lower bound with `cost_status = "partial"`, `is_lower_bound = true`, and `provisional_pass = true`.

```json
{
  "career_id": "software_developer",
  "career_name": "Software Developer",
  "domain": "tech_engineering",
  "data_status": "core",
  "pending_reason": null,
  "best_route": {
    "route_id": "route_sw_ju",
    "institution_name": "Jadavpur University (Faculty of Engineering & Technology)",
    "program_name": "B.E. Computer Science and Engineering",
    "duration_years": 4.0,
    "net_cost": 10900.0,
    "loan_needed": 0.0,
    "monthly_emi": 0.0,
    "repayment_burden": 0.05,
    "debt_service_ratio": 0.0,
    "payback_years": 0.08,
    "cost_status": "partial",
    "is_lower_bound": true,
    "provisional_pass": true
  },
  "alternative_routes": [
    {
      "route_id": "route_sw_iitm",
      "institution_name": "Indian Institute of Technology Madras",
      "program_name": "B.Tech Computer Science and Engineering",
      "net_cost": 1135950.0,
      "f_family": 72.07,
      "gate_cleared": 1,
      "cost_status": "complete"
    }
  ],
  "cost": {
    "total": 10900.0,
    "total_cost_known": 10900.0,
    "cost_status": "partial",
    "missing_fields": [
      "hostel",
      "mess"
    ],
    "is_lower_bound": true
  },
  "scores": {
    "fit": 84.77,
    "family_viability": 98.67,
    "market": null,
    "composite": 91.72,
    "final": 91.72
  },
  "gates": {
    "gate_financial": 1,
    "gate_academic": 1,
    "provisional_pass": true
  },
  "blocked": false,
  "blocked_cause": null,
  "funding_gap": null,
  "shortfall_details": null,
  "remedies": [],
  "blend_grid": [
    {"lambda": 0.0, "rank_score": 98.67, "rank": 1},
    {"lambda": 0.5, "rank_score": 91.72, "rank": 2},
    {"lambda": 1.0, "rank_score": 84.77, "rank": 6}
  ],
  "pareto": false,
  "balanced_pick": false,
  "sources": [
    {
      "field": "starting_salary",
      "source_url": "https://www.nielit.gov.in/",
      "retrieved_on": "2026-10-07"
    },
    {
      "field": "route_route_sw_ju_fee",
      "source_url": "http://www.jaduniv.edu.in/upload_files/admission_data/",
      "retrieved_on": "2026-10-07"
    }
  ],
  "stability_top3": 1.0
}
```

---

### Example 3: Blocked Career (`ux_designer` under restrictive loan cap)
Failed financial gate due to `loan_needed > loan_max`. Carries structured shortfall details and actionable bilingual remedies.

```json
{
  "career_id": "ux_designer",
  "career_name": "UX/UI Designer",
  "domain": "design_creative",
  "data_status": "core",
  "pending_reason": null,
  "best_route": {
    "route_id": "route_ux_iitb",
    "institution_name": "Indian Institute of Technology Bombay",
    "program_name": "B.Des (Bachelor of Design, IDC)",
    "duration_years": 4.0,
    "net_cost": 1107600.0,
    "loan_needed": 497600.0,
    "monthly_emi": 8260.75,
    "repayment_burden": 0.1326,
    "debt_service_ratio": 0.0536,
    "payback_years": 2.99,
    "cost_status": "complete",
    "is_lower_bound": false,
    "provisional_pass": false
  },
  "alternative_routes": [],
  "cost": {
    "total": 1107600.0,
    "total_cost_known": 1107600.0,
    "cost_status": "complete",
    "missing_fields": [],
    "is_lower_bound": false
  },
  "scores": {
    "fit": 79.97,
    "family_viability": 0.0,
    "market": null,
    "composite": 39.98,
    "final": 39.98
  },
  "gates": {
    "gate_financial": 0,
    "gate_academic": 1,
    "provisional_pass": false
  },
  "blocked": true,
  "blocked_cause": "loan_exceeds_cap",
  "funding_gap": 487600.0,
  "shortfall_details": {
    "grant_needed": 487600.0,
    "loan_needed": 497600.0,
    "loan_max": 10000.0,
    "monthly_emi": 8260.75
  },
  "remedies": [
    {
      "cause": "loan_exceeds_cap",
      "text_en": "The required education loan (₹497,600) exceeds your target limit of ₹10,000 by ₹487,600. Applying for merit/need-based government scholarships or looking at state quota options can bridge this ₹487,600 gap without straining family savings.",
      "text_hi": "इस कोर्स के लिए ₹497,600 के लोन की जरूरत है, जो आपकी तय सीमा (₹10,000) से ₹487,600 ज्यादा है। सरकारी स्कॉलरशिप या राज्य कोटे की सीट मिलने पर यह ₹487,600 की कमी आसानी से पूरी हो सकती है।",
      "action": "apply_scholarship"
    }
  ],
  "blend_grid": [
    {"lambda": 0.0, "rank_score": 0.0, "rank": 12},
    {"lambda": 0.5, "rank_score": 39.99, "rank": 12},
    {"lambda": 1.0, "rank_score": 79.97, "rank": 8}
  ],
  "pareto": false,
  "balanced_pick": false,
  "sources": [
    {
      "field": "starting_salary",
      "source_url": "https://www.nirfindia.org/2024/Declaration/Agreement/DCS/IR-O-U-0306.pdf",
      "retrieved_on": "2026-10-07"
    }
  ],
  "stability_top3": null
}
```

---

### Example 4: Pending Career (`ai_ml_engineer`)
Non-core career awaiting verified official routes and salary statistics. Excluded from ranking with explicit reason; missing values strictly returned as `null`.

```json
{
  "career_id": "ai_ml_engineer",
  "career_name": "AI / Machine Learning Engineer",
  "domain": "tech_engineering",
  "data_status": "pending",
  "pending_reason": "Pending data ingestion: unverified official routes and salaries",
  "best_route": null,
  "alternative_routes": [],
  "cost": {
    "total": null,
    "total_cost_known": null,
    "cost_status": "missing",
    "missing_fields": [
      "verified_route_costs",
      "verified_entry_salary"
    ],
    "is_lower_bound": false
  },
  "scores": {
    "fit": 84.77,
    "family_viability": null,
    "market": null,
    "composite": null,
    "final": null
  },
  "gates": {
    "gate_financial": null,
    "gate_academic": 1,
    "provisional_pass": false
  },
  "blocked": true,
  "blocked_cause": "not_enough_data",
  "funding_gap": null,
  "shortfall_details": null,
  "remedies": [],
  "blend_grid": [
    {"lambda": 0.0, "rank_score": null, "rank": null},
    {"lambda": 0.5, "rank_score": null, "rank": null},
    {"lambda": 1.0, "rank_score": null, "rank": null}
  ],
  "pareto": false,
  "balanced_pick": false,
  "sources": [],
  "stability_top3": null
}
```
