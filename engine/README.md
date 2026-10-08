# PRISM Engine (UDAAN Career Guidance Engine)

PRISM (Parent-Child Responsive Integrative Scoring Model) is the deterministic scoring and decision-engine powering UDAAN for DataQuest 3.0.

The engine provides pure functional APIs:
- Zero global mutable state.
- Strictly deterministic, seeded calculations.
- Strict data provenance: every non-None figure carries an official `source_url` and `retrieved_on`.
- Never fabricates or hallucinates numbers: missing figures remain strict Python `None`.

---

## Public Functions API Reference

### 1. `evaluate_family`
The primary single-call entrypoint for family career evaluation. Evaluates all 55 careers across student dimensional fit, parental financial viability, incomplete cost rules, 21-point lambda blend grids, and actionable bilingual remedies.

- **Signature**:
  ```python
  def evaluate_family(
      student_input: Student,
      parent_input: ParentProfile,
      options: Optional[Dict[str, Any]] = None
  ) -> Dict[str, Any]
  ```
- **Inputs**:
  - `student_input` (`Student`): Student profile including RIASEC scores, cognitive abilities, academic marks, and preferences.
  - `parent_input` (`ParentProfile`): Parent financial profile including household income, monthly budget, existing EMIs, risk tolerance, and loan willingness.
  - `options` (`Optional[Dict[str, Any]]`): Optional flags such as `loan_cap_override` (float) or custom thresholds.
- **Return Type**: `Dict[str, Any]` matching the shape defined in `docs/API_SHAPE.md` (top-level conflict diagnostics, dimension breakdowns, warnings, and list of career reports).
- **Example Call**:
  ```python
  from engine.public import evaluate_family
  from engine.student_fit.models import Student, AcademicProfile
  from engine.parent.models import ParentProfile, SectorRatings

  student = Student(
      student_id="student_01",
      stage="school",
      I_s={"R": 0.8, "I": 0.8, "A": 0.3, "S": 0.2, "E": 0.4, "C": 0.6},
      a_j={"logical": 0.8, "numerical": 0.8, "verbal": 0.7, "spatial": 0.6},
      academics=AcademicProfile(marks=85.0),
      risk_appetite=0.6,
      domain_preference={"tech_engineering": 5.0},
      relocation_willingness=0.8,
      max_years_to_income=4.0,
  )

  parent = ParentProfile(
      savings=1000000.0,
      monthly_surplus=50000.0,
      household_income=150000.0,
      existing_emis=10000.0,
      loan_max=1500000.0,
      domain_ratings={"tech_engineering": 5.0},
      sector_ratings=SectorRatings(govt=4, private=4, entrepreneurship=2),
      min_salary=600000.0,
      max_years_to_income=4.0,
      relocation_willingness=0.8,
      risk=0.5,
  )

  report = evaluate_family(student, parent, options={"loan_cap_override": 1000000.0})
  print("Conflict Index:", report["conflict_index"])
  print("Total Careers Evaluated:", len(report["careers"]))
  ```

---

### 2. `payback_range`
Runs a Monte Carlo simulation ($N=5000$, seeded and reproducible) to compute repayment years distribution for a route using a lognormal distribution fitted to official salary percentiles ($p10$ and $p90$).

- **Signature**:
  ```python
  def payback_range(
      route: Route,
      parent_input: ParentProfile,
      n: int = 5000,
      seed: int = 0
  ) -> Optional[Dict[str, Any]]
  ```
- **Inputs**:
  - `route` (`Route`): Verified route object with loan needed, tuition, duration, and salary percentiles.
  - `parent_input` (`ParentProfile`): Parent financial details.
  - `n` (`int`): Number of simulation iterations (default: 5000).
  - `seed` (`int`): PRNG seed for reproducible results (default: 0).
- **Return Type**: `Optional[Dict[str, Any]]`. Returns `None` with an explanatory note if $p10$ or $p90$ salary percentiles are absent. When present, returns `{p10_years, p50_years, p90_years, prob_within_horizon, horizon_years, histogram_bins, bin_edges, sample_size}`.
- **Example Call**:
  ```python
  from engine.public import payback_range
  from engine.parent.models import Route, ParentProfile

  route = Route(
      route_id="route_demo",
      career_id="software_developer",
      institution_name="Test Engineering College",
      tuition=800000.0,
      duration_years=4.0,
      starting_salary=1200000.0,
      p10_salary=800000.0,
      p90_salary=1800000.0,
      loan_needed=400000.0,
      source_url="https://official.edu/fees",
      retrieved_on="2026-10-08",
  )

  mc_result = payback_range(route, parent_input=parent, n=5000, seed=0)
  if mc_result:
      print("Median Payback (Years):", mc_result["p50_years"])
      print("Prob within 8 years:", mc_result["prob_within_horizon"])
  ```

---

### 3. `match_scholarships`
Matches verified national and state scholarship schemes against student academic qualifications and parental income levels using official eligibility criteria.

- **Signature**:
  ```python
  def match_scholarships(
      student_input: Student,
      parent_input: ParentProfile
  ) -> List[Dict[str, Any]]
  ```
- **Inputs**:
  - `student_input` (`Student`): Student profile.
  - `parent_input` (`ParentProfile`): Parent profile.
- **Return Type**: `List[Dict[str, Any]]` of eligible scholarships `{scheme_id, scheme_name, provider, amount_inr, deadline, match_reason, apply_url, retrieved_on}`.
- **Example Call**:
  ```python
  from engine.public import match_scholarships

  matches = match_scholarships(student, parent)
  for s in matches:
      print(f"{s['scheme_name']}: INR {s['amount_inr']} ({s['match_reason']})")
  ```

---

### 4. `overall_conflict`
Evaluates the holistic conflict between student preferences and parental aspirations across 4 dimensions (risk, domain, relocation, time horizon).

- **Signature**:
  ```python
  def overall_conflict(
      student: Student,
      parent: ParentProfile
  ) -> Dict[str, Any]
  ```
- **Inputs**:
  - `student` (`Student`)
  - `parent` (`ParentProfile`)
- **Return Type**: `Dict[str, Any]` returning `overall_conflict_score` (0-100) and `dimension_gaps` (0-1).
- **Example Call**:
  ```python
  from engine.public import overall_conflict

  conflict = overall_conflict(student, parent)
  print("Overall Conflict Score:", conflict["overall_conflict_score"])
  print("Dimension Gaps:", conflict["dimension_gaps"])
  ```

---

### 5. `per_career_scores`
Calculates student fit, parent viability, and feasibility gates on a per-career basis.

- **Signature**:
  ```python
  def per_career_scores(
      student: Student,
      parent: ParentProfile,
      careers: Optional[List[StudentCareer]] = None,
      routes: Optional[List[Route]] = None,
      market_records: Optional[List[CareerMarketRecord]] = None,
  ) -> Dict[str, Any]
  ```
- **Inputs**:
  - `student` (`Student`)
  - `parent` (`ParentProfile`)
  - Optional custom career / route / market lists.
- **Return Type**: `Dict[str, Any]` mapping `career_id` to `{student_fit, parent_viability, gate_cleared, best_route_id, ...}`.
- **Example Call**:
  ```python
  from engine.public import per_career_scores

  scores = per_career_scores(student, parent)
  print("Software Developer Scores:", scores["careers"].get("software_developer"))
  ```

---

### 6. `negotiate`
Evaluates compromise zone rankings across the $\alpha$ weighting spectrum between student fit and parental financial viability.

- **Signature**:
  ```python
  def negotiate(
      student: Student,
      parent: ParentProfile,
      alpha: float = 0.50,
      careers: Optional[List[StudentCareer]] = None,
      routes: Optional[List[Route]] = None,
      market_records: Optional[List[CareerMarketRecord]] = None,
  ) -> Dict[str, Any]
  ```
- **Inputs**:
  - `student` (`Student`)
  - `parent` (`ParentProfile`)
  - `alpha` (`float`): Student weight $\alpha \in [0.0, 1.0]$.
- **Return Type**: `Dict[str, Any]` returning ranked compromise careers, Pareto frontier indicators, and balanced pick.
- **Example Call**:
  ```python
  from engine.public import negotiate

  result = negotiate(student, parent, alpha=0.60)
  print("Balanced Pick:", result["balanced_pick"])
  ```

---

### 7. `unified_roadmap`
Synthesizes the end-to-end full family career roadmap report.

- **Signature**:
  ```python
  def unified_roadmap(
      student: Student,
      parent: ParentProfile,
      alpha: float = 0.50,
      careers: Optional[List[StudentCareer]] = None,
      routes: Optional[List[Route]] = None,
      market_records: Optional[List[CareerMarketRecord]] = None,
      student_region: Optional[str] = None,
  ) -> FullRoadmapReport
  ```
- **Inputs**:
  - Profiles, alpha slider, optional catalogues and regional filter.
- **Return Type**: `FullRoadmapReport` dataclass.
- **Example Call**:
  ```python
  from engine.public import unified_roadmap

  roadmap = unified_roadmap(student, parent, alpha=0.50)
  print("Recommended Careers:", [item.career_id for item in roadmap.top_recommendations])
  ```
