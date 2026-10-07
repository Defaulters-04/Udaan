# PRISM Engine - Parent Machine Module

The **Parent Machine** module of the **PRISM Engine** (`UDAAN`) implements the core financial constraint solver, affordability verification, and parental family fit scoring ($F_{family}$). It evaluates educational pathways (routes) against household financial realities, risk appetite, and aspiration profiles.

---

## 1. Architecture Overview

```
prism/parent/
├── __init__.py           # Package exports
├── config.py             # Dataclass with all parameterized thresholds and weights
├── models.py             # Pydantic v2 schemas with validation and units in INR
├── solver.py             # Pure math constraint solver functions
├── scores.py             # Pure math sub-score calculators and portfolio evaluator
├── api.py                # Thin FastAPI wrapper with /parent/evaluate and /parent/config
├── demo.py               # Illustrative demo script printing tabular evaluation
├── README.md             # Architecture, formulas, and usage documentation
└── tests/                # Test suite with 100% pytest pass rate
    ├── __init__.py
    ├── test_parent_solver.py  # Sanity case, gates, edge cases, property tests
    └── test_api.py            # FastAPI endpoint tests
```

---

## 2. Mathematical Formulas

Every mathematical function is deterministic, typed, and pure.

### 2.1 Net Educational Cost ($N_r$)
$$N_r = \max(0, T + L + E_{exam} - G)$$
Where:
- $T$: Tuition fee (INR)
- $L$: Living / hostel expenses (INR)
- $E_{exam}$: Entrance exam and equipment costs (INR)
- $G$: Scholarships / grants (INR)

### 2.2 Family Cash Capacity ($A_{cash}$)
$$A_{cash} = 0.50 \cdot S + 12 \cdot Y \cdot 0.25 \cdot M$$
Where:
- $S$: Total liquid savings (INR)
- $M$: Monthly uncommitted disposable cash surplus (INR)
- $Y$: Course duration in years
- Constants: 50% savings liquidation share, 25% surplus commitment share.

### 2.3 Loan Requirement & Repayment ($L_{need}$, $EMI$)
$$L_{need} = \max(0, N_r - A_{cash})$$
$$EMI = L_{need} \cdot \frac{i(1+i)^n}{(1+i)^n - 1}$$
Where:
- $i = \frac{\text{annual\_rate}}{12}$ (default 10% annual rate $\implies i = 0.10 / 12$)
- $n = \text{term\_months}$ (default 7 years $\implies 84$ months)
- If $L_{need} = 0$, $EMI = 0$. If $i = 0$, $EMI = L_{need} / n$.

### 2.4 Debt Burden Indicators ($RB$, $DSR$)
- **Parent Repayment Burden ($RB$):**
  $$RB = \frac{E_{exist} + EMI}{M_{inc}}$$
  Where $E_{exist}$ is existing monthly EMIs and $M_{inc}$ is gross monthly household income.
- **Student Debt Service Ratio ($DSR$):**
  $$DSR = \frac{12 \cdot EMI}{Y_1}$$
  Where $Y_1$ is expected gross annual starting salary.

### 2.5 Feasibility Gates ($G_{fin}$, $G$)
$$A_{family} = A_{cash} + L_{max}$$
$$G_{fin} = \begin{cases} 1 & \text{if } L_{need} \le L_{max} \land RB \le 0.50 \land DSR \le 0.20 \\ 0 & \text{otherwise} \end{cases}$$
$$G = G_{fin} \cdot g_{acad}$$
*(Where $g_{acad} \in \{0, 1\}$ defaults to 1).*

### 2.6 Financial Sub-scores ($F_{financial} \in [0, 100]$)
- $F_{budget} = \max\left(0, 1 - \frac{N_r}{A_{family}}\right)$
- $F_{repay\_p} = \text{clamp}\left(1 - \frac{\max(0, RB - 0.30)}{0.20}\right)$
- $F_{dsr} = \text{clamp}\left(1 - \frac{\max(0, DSR - 0.10)}{0.10}\right)$
- $\text{Payback} = \frac{N_r}{0.20 \cdot Y_1}$ years; $\quad F_{payback} = \max\left(0, 1 - \frac{\text{Payback}}{8}\right)$
- **Composite Financial Score:**
  $$F_{financial} = 100 \cdot (0.35 F_{budget} + 0.25 F_{repay\_p} + 0.25 F_{dsr} + 0.15 F_{payback})$$

### 2.7 Aspirational Sub-scores ($F_{aspiration} \in [0, 100]$)
- $f_{domain} = \frac{\text{rating} - 1}{4} \in [0, 1]$
- $f_{sector} = \frac{\text{rating} - 1}{4} \in [0, 1]$
- $f_{salary} = \min\left(1, \frac{Y_1}{Sal_p}\right) \in [0, 1]$
- $f_{time} = \min\left(1, \frac{T_p}{t_r}\right) \in [0, 1]$ (if $t_r = 0$, $f_{time} = 1.0$)
- $f_{location} = 1 - \max(0, \rho_c - \rho_p) \in [0, 1]$
- **Composite Aspiration Score:**
  $$F_{aspiration} = 100 \cdot (0.30 f_{domain} + 0.15 f_{sector} + 0.20 f_{salary} + 0.20 f_{time} + 0.15 f_{location})$$

### 2.8 Risk Alignment ($F_{risk} \in [0, 100]$)
$$F_{risk} = 100 \cdot (1 - \max(0, R_c - R_p))$$
Where $R_p = \frac{GL - 13}{34}$ when using Gardner-Likert assessment ($GL \in [13, 47]$).

### 2.9 Total Composite Family Score ($F_{family}$)
$$F_{family}(route) = G \cdot (0.50 F_{financial} + 0.30 F_{aspiration} + 0.20 F_{risk})$$
For any career:
$$F_{family}(career) = \max_{r \in \text{routes}} F_{family}(r)$$

---

## 3. Configuration & Sensitivity Testing

All parameters are encapsulated in `ParentSolverConfig` in `config.py`:
```python
from prism.parent.config import ParentSolverConfig, DEFAULT_CONFIG

# Easy sensitivity test (+20% loan interest rate)
stressed_config = DEFAULT_CONFIG.with_overrides(annual_loan_rate=0.12)
```

---

## 4. API Endpoints

Launch the FastAPI server:
```bash
uvicorn prism.parent.api:app --reload --port 8000
```

### `GET /parent/config`
Returns active default parameters.

### `POST /parent/evaluate`
Accepts `ParentEvaluationRequest` containing `profile`, `routes`, and optional `config` overrides. Returns:
- `career_results`: Best route and alternatives ranked by $F_{family}$.
- `reports`: Exhaustive viability report per route.
- `blocked_list`: Feasibility deficits with calculated grant shortfalls and alternative routes.

---

## 5. Running the Tests & Demo

```bash
# Run test suite
pytest prism/parent/tests/ -v

# Run illustrative CLI demo
python -m prism.parent.demo
```
