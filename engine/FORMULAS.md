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
- **Interest Fit ($InterestFit$):** (Fix 6)
  Blends Pearson correlation and Top-3 RIASEC code overlap:
  $$interest\_term = 50.0 \cdot (1.0 + r)$$
  $$overlap\_term = 100.0 \cdot \frac{|\text{top3}(I_s) \cap \text{top3}(I_c)|}{3}$$
  $$InterestFit = w_{pearson} \cdot interest\_term + w_{overlap} \cdot overlap\_term$$
  *(Weights in config: $w_{pearson} = 0.50, w_{overlap} = 0.50$).*
  *If student RIASEC standard deviation is below config cutoff (`std_dev < 0.02`), returns $InterestFit = 50.0$ and sets `low_signal = True`.*

- **Aptitude Fit ($AptitudeFit$):**
  Penalizes only cognitive shortfalls below required threshold $c_j$:
  $$AptitudeFit = 100 \cdot \left[ 1.0 - \frac{\sum_j u_j \cdot \max(0, c_j - a_j)}{\sum_j u_j \cdot c_j} \right]$$

- **Stretch Flag:** (Fix 3)
  Computed via weighted aptitude shortfall ratio:
  $$\text{shortfall\_ratio} = \frac{\sum_j u_j \cdot \max(0, c_j - a_j)}{\sum_j u_j \cdot c_j}$$
  If $\text{shortfall\_ratio} > \text{stretch\_shortfall\_ratio}$ (config: 0.20, design assumption), sets `stretch = True` and attaches the specific aptitude shortfall reasons. Stretch careers are **NOT** blocked and retain their full score.

- **Missing Data Handling:** (Fix 4)
  Any input or sub-score that is `None` or `"NOT FOUND"` is dropped from the weighted sum, and the remaining weights are rescaled to total 1.0. Never substitutes a default number. Careers receive `data_confidence` ("high", "medium", "low") based on the fraction of dropped weight.

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
- Component weights: $w_{fin} = 0.50, \quad w_{asp} = 0.30, \quad w_{risk} = 0.20$

### 2.2 Financial Gate ($G_{fin}$) & Explicit Configured Thresholds (Fix 7)
All financial thresholds are parameterised in `ParentSolverConfig` with the comment `design assumption, unsourced, verify against bank lending norms`:
1. $L_{needed} \le L_{max}$ (Required educational loan within borrowing willingness)
2. $Cost_{net} \le Cash_{avail} + L_{max}$ (Total net educational cost within combined liquidity)
3. $RB \le rb\_gate\_max$ (`0.50`, Repayment burden gate max)
4. $DSR \le dsr\_gate\_max$ (`0.20`, Total debt service ratio gate max)

**Missing Salary / Route Cost Behavior (Fix 4):**
If route tuition or starting salary is missing (`None` or `"NOT FOUND"`), the financial solver returns status `"insufficient_data"` and $F_{family} = 0.0, G_{fin} = 0$. The career is excluded from the compromise zone with the missing data reason stated.

### 2.3 Financial Sub-Scores ($f_{financial}$) with Weight Rescaling (Fix 4)
$$f_{financial} = \frac{\sum_{i \in \text{available}} w_i \cdot f_i}{\sum_{i \in \text{available}} w_i}$$
Where:
- $f_{budget} = \max\left(0, 1 - \frac{\text{funding\_gap}}{Cost_{net}}\right)$
- $f_{repay\_p} = \text{clamp}\left(1 - \frac{\max(0, RB - rb\_comfort\_threshold)}{rb\_penalty\_range}\right)$
- $f_{dsr} = \text{clamp}\left(1 - \frac{\max(0, DSR - dsr\_comfort\_threshold)}{dsr\_penalty\_range}\right)$
- $f_{payback} = \text{clamp}\left(1 - \frac{\text{Payback}}{payback\_horizon\_years}\right)$

---

## 3. Payback Period Figure

**Source:** `engine/parent/scores.py`

### 3.1 Point Estimate
$$\text{Payback} = \frac{N_r}{payback\_income\_share \cdot Y_1}$$
Where `payback_income_share` = `0.20` and `payback_horizon_years` = `8.0` (design assumptions in config).

---

## 4. Conflict Index ($C_{family}$) vs Per-Career Fit Gap ($fit\_gap$) (Fix 1 & Fix 2)

**Source:** `engine/conflict/scores.py`, `engine/conflict/config.py`

### 4.1 Overall Family Conflict Index (Diagnostic Only)
$$C_{family} = 0.25 \cdot Gap_{risk} + 0.25 \cdot Gap_{domain} + 0.25 \cdot Gap_{relocation} + 0.25 \cdot Gap_{time}$$
- **Fix 1:** Conflict Index is strictly diagnostic. It **never** alters scores or rankings. The old composite multiplier $(1 - 0.10 \cdot conflict / 100)$ is completely deleted.
- **Fix 2:** The term "conflict" refers solely to the student-vs-parent Conflict Index. The per-career $|Fit - Family|$ divergence is renamed everywhere to $fit\_gap$.

### 4.2 Per-Career Fit Gap ($fit\_gap$)
$$fit\_gap = |F_{student} - F_{family}|$$

---

## 5. Market Machine Tiers (Fix 5)

**Source:** `engine/market/components.py`, `engine/market/config.py`

- Percentile rank scoring across the catalogue is replaced with absolute signal tiers:
  - Demand: `rising`, `stable`, `declining`
  - Velocity: `rising`, `stable`, `declining`
  - Disruption: `low`, `medium`, `high`
- Tiers map to points via a lookup table in config (no shrinkage toward 50).
- Market is **not** part of any composite and **not** on the slider. It is displayed as a badge (`demand_tier`, `confidence`, `evidence_level`) and used solely as a tiebreaker when two careers have equal ranking score.

---

## 6. Negotiation Explorer Slider & 2-Score Ranking (Fix 8)

**Source:** `engine/conflict/scores.py`, `engine/synthesis.py`

Final ranking uses exactly two scores: Fit ($F_{student}$) and Family ($F_{family}$):
$$\text{Ranking}(\lambda) = \lambda \cdot F_{student} + (1 - \lambda) \cdot F_{family}, \quad \lambda \in [0.0, 1.0]$$

- Tiebreaker: When two careers have identical negotiated scores, higher Market tier points break the tie.
- All alternative formulas (the 0.45/0.25/0.15/0.15 Fit variant, 6-component Family variant, and composite multiplier) are deleted.

---

## 7. Balanced Pick & Compromise Zone (Fix 8)

**Source:** `engine/conflict/scores.py`

### 7.1 Balanced Pick
$$\text{Balanced Pick} = \arg\max_{c \in \text{viable}} \min(F_{student}(c), F_{family}(c))$$

### 7.2 Compromise Zone
The Compromise Zone is the **Pareto frontier** among careers satisfying:
1. $F_{student} \ge \tau_{student}$ (`0.50`, default cutoff in config, design assumption)
2. $F_{family} \ge \tau_{family}$ (`0.50`, default cutoff in config, design assumption)
3. Financial gate passed ($G_{fin} == 1$, status $\ne$ `"insufficient_data"`)

A career in this candidate set is included in the Compromise Zone iff it is non-dominated by any other candidate in the $(F_{student}, F_{family})$ space.

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
