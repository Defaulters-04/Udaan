# PRISM Engine - Conflict Index & Negotiation Explorer Module

The **Conflict Index** module of the **PRISM Engine** (`UDAAN`) quantifies and explains misalignment between students and parents across shared decision dimensions. It powers **Page 5 (Family Mirror)** and **Page 6 (Negotiation Explorer)** of the Udaan platform, finding high-viability compromise career routes both sides can accept without financial strain or family dispute.

---

## 1. Architecture Overview

```
engine/conflict/
├── __init__.py           # Clean package exports
├── config.py             # ConflictConfig dataclass with parameterized weights & thresholds
├── models.py             # Pydantic v2 data models for diagnoses, routes, and negotiation
├── scores.py             # Pure deterministic scoring algorithms, explanations & Pareto solver
├── api.py                # FastAPI thin wrapper with endpoints (/conflict/overall, /conflict/career, /conflict/negotiate)
├── demo.py               # Interactive CLI demonstration script
├── README.md             # Architectural and mathematical documentation
└── tests/                # 100% passing pytest test suite
    ├── __init__.py
    ├── test_conflict.py    # Dimension gaps, sanity cases, and property invariants
    ├── test_negotiation.py # Negotiation slider, Pareto frontier, and composite blending
    └── test_api.py         # FastAPI endpoints integration tests
```

---

## 2. Shared Dimensions & Mathematical Formulas

All mathematical functions are deterministic, typed, clamped in $[0, 1]$, and pure.

### 2.1 The Four Shared Dimensions

| Shared Dimension | Student Parameter | Parent Parameter | Domain / Scale |
| :--- | :--- | :--- | :--- |
| **Risk Appetite** | `risk_appetite` ($R_s$) | `risk` ($R_p$) | $[0, 1]$ (0 = risk-averse, 1 = risk-seeking) |
| **Domain Preferences** | `domain_preference` | `domain_ratings` | $1.0$ to $5.0$ rating scale per sector |
| **Relocation Willingness** | `relocation_willingness` ($\rho_s$) | `relocation_willingness` ($\rho_p$) | $[0, 1]$ (0 = stay local, 1 = move anywhere) |
| **Time to First Income** | `max_years_to_income` ($T_s$) | `max_years_to_income` ($T_p$) | Years ($\ge 0$) until gainful employment |

---

### 2.2 Normalized Dimension Gaps

1. **Risk Appetite Gap ($G_{risk}$):**
   $$G_{risk} = |R_s - R_p|$$

2. **Domain Misalignment Gap ($G_{domain}$):**
   $$G_{domain} = \frac{1}{|D|} \sum_{d \in D} \frac{|s(d) - p(d)|}{5.0 - 1.0}$$
   Where $D$ is the union of domains rated by either stakeholder (missing domains defaulted to neutral 3.0).

3. **Relocation Willingness Gap ($G_{relocation}$):**
   $$G_{relocation} = |\rho_s - \rho_p|$$

4. **Time Horizon Gap ($G_{time}$):**
   $$G_{time} = \frac{|T_s - T_p|}{\max(T_s, T_p, 1.0)}$$
   *Note: Normalized by the larger horizon so a 2-year difference between 2y and 4y targets (100% gap) is penalized more severely than between 8y and 10y targets (20% gap).*

---

### 2.3 Overall Family Conflict Index ($C_{family}$)

$$C_{family} = w_{risk} \cdot G_{risk} + w_{domain} \cdot G_{domain} + w_{reloc} \cdot G_{relocation} + w_{time} \cdot G_{time}$$

Where default weights are equal ($w_i = 0.25$, $\sum w_i = 1.00$).

**High Conflict Flag:**
$$\text{is\_high\_conflict} = \mathbb{I}\left(\max(G_{risk}, G_{domain}, G_{relocation}, G_{time}) > \tau_{conflict}\right)$$
Default threshold $\tau_{conflict} = 0.40$.

---

### 2.4 Per-Career Route Conflict Index ($C_{route}$)

For a specific candidate educational route $r$:
- **Student Route Fit:** Evaluates student affinity with the route's risk, domain, relocation demand, and duration.
- **Parent Route Fit:** Evaluates parent affinity with the same route attributes.
- **Per-Dimension Fit Gaps:**
  $$\Delta_{dim} = |\text{fit}_{student}(dim) - \text{fit}_{parent}(dim)|$$
- **Route Conflict Score:**
  $$C_{route} = \sum_{dim} w_{dim} \cdot \Delta_{dim}$$

---

### 2.5 Negotiation Explorer Slider ($\alpha$)

The user slider balances student aspiration vs family financial feasibility:
- $\alpha = 1.0$: $100\%$ Student Priority
- $\alpha = 0.5$: Balanced Compromise
- $\alpha = 0.0$: $100\%$ Parent / Family Feasibility Priority

**Negotiated Score:**
$$S_{negotiated} = \alpha \cdot F_{student} + (1 - \alpha) \cdot F_{family} - \lambda_{conflict} \cdot C_{route}$$
Where default conflict penalty coefficient $\lambda_{conflict} = 0.15$.

**The Compromise Zone:**
A career route qualifies for the **Compromise Zone** if:
$$F_{student} \ge \tau_{student\_min} \quad \wedge \quad F_{family} \ge \tau_{family\_min} \quad \wedge \quad G_{financial} = \text{PASS}$$
*(Default thresholds $\tau_{student\_min} = 0.50$, $\tau_{family\_min} = 0.50$)*

**Pareto Frontier:**
A career $A$ is Pareto optimal if no other career $B$ exists such that:
$$F_{student}(B) \ge F_{student}(A) \quad \text{and} \quad F_{family}(B) \ge F_{family}(A)$$
with at least one strict inequality.

---

### 2.6 Composite Career Score Blending

Blends Student Fit, Family Viability, and Market Machine score into a final unified score:
$$\text{Base} = w_s \cdot F_{student} + w_f \cdot F_{family} + w_m \cdot F_{market}$$
$$\text{Composite} = \text{clamp}\left(\text{Base} \cdot (1 - \lambda_{conflict} \cdot C_{route})\right)$$

---

## 3. FastAPI Service Endpoints

The module includes a lightweight FastAPI service in `engine/conflict/api.py`:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/conflict/config` | Retrieve current parameter weights and thresholds |
| `POST` | `/conflict/overall` | Evaluate overall family diagnosis and narrative explanations |
| `POST` | `/conflict/career` | Evaluate conflict for an individual route |
| `POST` | `/conflict/evaluate` | Evaluate portfolio of routes against family profiles |
| `POST` | `/conflict/negotiate` | Run the Negotiation Explorer slider and identify compromise zone |
| `GET` | `/conflict/health` | Health check probe |

---

## 4. Running the Demo and Test Suite

```bash
# Run the interactive CLI demonstration
python engine/conflict/demo.py

# Run all unit and integration tests
pytest engine/conflict/tests/ -v
```
