# PRISM Engine — Mathematical Formulas & Weights Specification

This document records the exact mathematical formulas, weights, gating rules, and simulation parameters as implemented in the PRISM Engine codebase.

All formulas and parameters are copied directly from the implementation files.

---

## 1. Student Fit ($F_{student}$)

**Source:** `engine/student_fit/scoring.py`, `engine/student_fit/config.py`

### 1.1 Composite Student Fit
$$F_{student} = G_{acad} \cdot \left( w_I \cdot InterestFit + w_A \cdot AptitudeFit + w_S \cdot SkillFit + w_P \cdot PersonalityFit \right)$$
Range: $[0.0, 100.0]$

### 1.2 Academic Gate ($G_{acad}$)
$$G_{acad} = \begin{cases} 1 & \text{if marks } \ge min\_marks \text{ AND all required subjects present AND all required exams present} \\ 0 & \text{otherwise} \end{cases}$$

### 1.3 Stage Weights (`STAGE_WEIGHTS`)
| Stage | $w_I$ (Interest) | $w_A$ (Aptitude) | $w_S$ (Skill) | $w_P$ (Personality) |
| :--- | :--- | :--- | :--- | :--- |
| **School** | `0.50` | `0.30` | `0.10` | `0.10` |
| **College** | `0.40` | `0.30` | `0.20` | `0.10` |

### 1.4 Sub-Component Scoring Formulas
- **Interest Fit ($InterestFit$):**
  Uses Pearson correlation $r$ between student RIASEC vector $I_s$ and career benchmark $I_c$:
  $$r = \frac{\sum (I_s - \bar{I}_s)(I_c - \bar{I}_c)}{\sqrt{\sum (I_s - \bar{I}_s)^2 \sum (I_c - \bar{I}_c)^2}}$$
  $$InterestFit = 50.0 \cdot (1.0 + r)$$
  *(If either profile has zero variance, $InterestFit = 50.0$ neutral).*

- **Aptitude Fit ($AptitudeFit$):**
  Penalizes only cognitive shortfalls below required threshold $c_j$:
  $$AptitudeFit = 100 \cdot \left[ 1.0 - \frac{\sum_j u_j \cdot \max(0, c_j - a_j)}{\sum_j u_j \cdot c_j} \right]$$

- **Skill Fit ($SkillFit$):**
  $$SkillFit = 100 \cdot \left[ 1.0 - \frac{\sum_k s_k \cdot \max(0, R_k - P_k)}{\sum_k s_k \cdot R_k} \right]$$
  *(If required skills $R_k$ empty, $SkillFit = 100.0$).*

- **Personality Fit ($PersonalityFit$):**
  Weighted Euclidean distance across Big Five dimensions:
  $$PersonalityFit = 100 \cdot \left[ 1.0 - \sqrt{\frac{\sum_j v_j \cdot (P_j - Pc_j)^2}{\sum_j v_j}} \right]$$

---

## 2. Family Viability ($F_{family}$)

**Source:** `engine/parent/scores.py`, `engine/parent/config.py`

### 2.1 Composite Family Viability
$$F_{family} = G \cdot \left[ w_{fin} \cdot f_{financial} + w_{asp} \cdot f_{aspiration} + w_{risk} \cdot f_{risk} \right] \times 100$$
Where:
- $G = G_{fin} \cdot g_{acad}$
- Component weights: $w_{fin} = 0.50, \quad w_{asp} = 0.35, \quad w_{risk} = 0.15$

### 2.2 Financial Gate ($G_{fin}$)
$G_{fin} = 1$ if and only if ALL four conditions hold:
1. $L_{needed} \le L_{max}$ (Required educational loan within borrowing willingness)
2. $Cost_{net} \le Cash_{avail} + L_{max}$ (Total net educational cost within combined liquidity)
3. $RB \le 0.30$ (Monthly repayment burden $\le 30\%$ of monthly household income)
4. $DSR \le 0.40$ (Total debt service ratio $\le 40\%$ of monthly household income)

### 2.3 Financial Sub-Scores ($f_{financial}$)
$$f_{financial} = 0.35 \cdot f_{budget} + 0.25 \cdot f_{repay\_p} + 0.25 \cdot f_{dsr} + 0.15 \cdot f_{payback}$$
Where:
- $f_{budget} = \max\left(0, 1 - \frac{\text{funding\_gap}}{Cost_{net}}\right)$
- $f_{repay\_p} = \max\left(0, 1 - \frac{RB}{0.30}\right)$
- $f_{dsr} = \max\left(0, 1 - \frac{DSR}{0.40}\right)$
- $f_{payback} = \max\left(0, 1 - \frac{\text{Payback}}{8.0}\right)$

### 2.4 Aspiration Sub-Scores ($f_{aspiration}$)
$$f_{aspiration} = 0.30 \cdot f_{domain} + 0.15 \cdot f_{sector} + 0.20 \cdot f_{salary} + 0.20 \cdot f_{time} + 0.15 \cdot f_{location}$$
Where:
- $f_{domain} = \frac{\text{rating} - 1.0}{4.0}$
- $f_{sector} = \frac{\text{sector\_rating} - 1.0}{4.0}$
- $f_{salary} = \min\left(1.0, \frac{Y_1}{Sal_p}\right)$
- $f_{time} = 1.0 \text{ if } t_r \le T_p \text{ else } \max\left(0, 1 - \frac{t_r - T_p}{3.0}\right)$
- $f_{location} = 1.0 - \max(0, \rho_c - \rho_p)$

### 2.5 Risk Sub-Score ($f_{risk}$)
$$f_{risk} = 1.0 - |R_c - R_p|$$

---

## 3. Payback Period Figure

**Source:** `engine/parent/scores.py` (lines 62–85)

### 3.1 Point Estimate
The payback figure is a **deterministic point estimate** (single scalar in years):
$$\text{Payback} = \frac{N_r}{0.20 \cdot Y_1}$$
Where:
- $N_r = \text{net\_cost}$ (Total tuition + living + exam fees after grants)
- $Y_1 = \text{starting\_salary}$ (Annual gross entry salary)
- `payback_income_share` = `0.20` (assumes 20% of graduate starting salary allocated to debt service)

**Boundary conditions:**
- If $N_r \le 0$: $\text{Payback} = 0.0$ years.
- If $Y_1 \le 0$: $\text{Payback} = 99.0$ years (unbounded horizon).
- Clamped for scoring to `payback_horizon_years` = `8.0` years:
  $$F_{payback} = \max\left(0.0, 1.0 - \frac{\text{Payback}}{8.0}\right)$$

---

## 4. Conflict Index ($C_{family}, C_{route}$)

**Source:** `engine/conflict/scores.py`, `engine/conflict/config.py`

### 4.1 Overall Family Conflict Index
$$C_{family} = 0.25 \cdot Gap_{risk} + 0.25 \cdot Gap_{domain} + 0.25 \cdot Gap_{relocation} + 0.25 \cdot Gap_{time}$$
Where each gap is normalized to $[0.0, 1.0]$:
- $Gap_{risk} = |R_s - R_p|$
- $Gap_{domain} = \frac{1}{|D|} \sum_{d \in D} \frac{|s(d) - p(d)|}{4.0}$
- $Gap_{relocation} = |\rho_s - \rho_p|$
- $Gap_{time} = \frac{|T_s - T_p|}{10.0}$

A family is classified as **High Conflict** iff $C_{family} \ge 0.50$ (50%).

### 4.2 Route-Specific Conflict ($C_{route}$)
$$C_{route} = 0.25 \cdot Gap_{risk}(c) + 0.25 \cdot Gap_{domain}(c) + 0.25 \cdot Gap_{reloc}(c) + 0.25 \cdot Gap_{time}(c)$$

---

## 5. Composite Score ($S_{comp}$)

**Source:** `engine/conflict/scores.py` (lines 472–500)

$$base = \frac{w_{student} \cdot F_{student} + w_{family} \cdot F_{family} + w_{market} \cdot F_{market}}{w_{student} + w_{family} + w_{market}}$$
$$penalty = conflict\_penalty\_weight \cdot C_{route} \cdot base$$
$$S_{comp} = \text{clamp}(base - penalty)$$

**Weights:**
- $w_{student} = 0.40$
- $w_{family} = 0.35$
- $w_{market} = 0.25$
- $conflict\_penalty\_weight = 0.20$

---

## 6. Negotiation Explorer Slider & Ranking

**Source:** `engine/conflict/scores.py` (lines 580–584)

For slider balance $\alpha \in [0.0, 1.0]$:
$$base(\alpha) = \alpha \cdot F_{student} + (1.0 - \alpha) \cdot F_{family}$$
$$penalty = conflict\_penalty\_weight \cdot C_{route}$$
$$S_{negotiated}(\alpha) = \text{clamp}(base(\alpha) - penalty)$$

**Slider Anchor Positions:**
- $\alpha = 0.0$: 100% Parent Priority
- $\alpha = 0.5$: Balanced / Compromise Priority
- $\alpha = 1.0$: 100% Student Priority
- Conflict Penalty: $conflict\_penalty\_weight = 0.20$

---

## 7. Compromise Zone Definition

**Source:** `engine/conflict/scores.py` (line 585), `engine/conflict/config.py`

A career qualifies in the **Compromise Zone** if and only if ALL three conditions hold:
$$F_{student} \ge \tau_{student} \quad \text{AND} \quad F_{family} \ge \tau_{family} \quad \text{AND} \quad is\_financially\_viable == \text{True}$$

**Configured Thresholds:**
- $\tau_{student} = 0.50$ (Student Fit $\ge 50\%$)
- $\tau_{family} = 0.50$ (Family Viability $\ge 50\%$)
- $G_{fin} == 1$ (Feasible educational route within family borrowing/repayment capacity)

---

## 8. Pareto Optimality Rule

**Source:** `engine/conflict/scores.py` (lines 503–523)

In the two-objective optimization space $(F_{student}, F_{family})$:
A career $A$ is **Pareto Dominated** by career $B$ if and only if:
$$F_{student}(B) \ge F_{student}(A) \quad \text{AND} \quad F_{family}(B) \ge F_{family}(A)$$
with at least one strict inequality:
$$F_{student}(B) > F_{student}(A) \quad \text{OR} \quad F_{family}(B) > F_{family}(A)$$

A career is classified as **Pareto Optimal** ($is\_pareto\_optimal = \text{True}$) if and only if no other viable career dominates it.

---

## 9. Monte Carlo Sensitivity Analysis

**Source:** `engine/market/sensitivity.py` (lines 40–85)

### 9.1 What is Perturbed
The Monte Carlo simulation perturbs the **five component weights** of the Market Machine ($F_{market}$):
1. `w_demand_level` (Base weight: `0.35`)
2. `w_trend` (Base weight: `0.25`)
3. `w_pay_yield` (Base weight: `0.15`)
4. `w_low_disruption` (Base weight: `0.15`)
5. `w_local_demand` (Base weight: `0.10`)

### 9.2 Perturbation Distribution & Mechanism
For each simulation run $k \in \{1, \dots, N\}$:
$$\text{multiplier}_j \sim \text{Uniform}(1.0 - \delta, 1.0 + \delta) = \text{Uniform}(0.80, 1.20)$$
Where $\delta = sensitivity\_perturbation = 0.20$ ($\pm 20\%$).

Perturbed weights:
$$w_j^{(k)} = w_j^{base} \cdot \text{multiplier}_j$$

Renormalization per career based on available data mask $M_{c, j} \in \{0, 1\}$:
$$\tilde{w}_{c, j}^{(k)} = \frac{M_{c, j} \cdot w_j^{(k)}}{\sum_m M_{c, m} \cdot w_m^{(k)}}$$

Simulated market score for career $c$:
$$F_{market}^{(k)}(c) = \sum_j \tilde{w}_{c, j}^{(k)} \cdot \text{scaled\_component}_{c, j} \times 100.0$$

### 9.3 Simulation Parameters
- Runs: $N = 1000$ iterations
- Random Number Generator: `numpy.random.default_rng(seed=0)` (deterministic)
- Stability Metrics Computed:
  - `top_3_stability_share`: Percentage of runs career $c$ remains among top 3 careers.
  - `rank_shift_3_or_more_share`: Percentage of runs where career $c$ shifts by $\ge 3$ rank positions relative to baseline.
