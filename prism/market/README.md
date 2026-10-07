# PRISM Engine - Market Machine Module

The **Market Machine** module of the **PRISM Engine** (`UDAAN`) calculates a family-independent labour market score $F_{market} \in [0, 100]$ with an honest uncertainty range ($F_{market}^{pessimistic}$, $F_{market}^{central}$, $F_{market}^{optimistic}$) and data-confidence audits.

---

## 1. Architecture Overview

```
prism/market/
├── __init__.py           # Package exports
├── config.py             # MarketSolverConfig dataclass (+/-20% sensitivity support)
├── models.py             # Pydantic v2 schemas with validation and units in INR
├── data_loader.py        # Strict JSON snapshot loading & schema validation
├── forecast.py           # Series cleaning, gap interpolation & forecasting ladder (ETS, OLS, Curated)
├── components.py         # Component calculators (demand, trend, pay yield, disruption, local LQ)
├── scores.py             # Composite scoring, uncertainty variants & explanation generator
├── handoff.py            # Multi-machine handoff (conflict, composite, final, gating)
├── sensitivity.py        # Monte Carlo weight perturbation analysis
├── api.py                # Thin FastAPI wrapper
├── demo.py               # Standalone demo script printing ranked evaluation table
├── README.md             # Technical documentation
└── tests/
    ├── __init__.py
    ├── test_market_solver.py  # Tests 1-15 covering formulas, monotonicity, determinism, property tests
    └── test_api.py            # FastAPI endpoints testing
```

---

## 2. Mathematical Components ($c_k \in [0, 1]$)

1. **Demand Level ($c_{demand}$)**:
   $$\text{base\_level} = \text{mean}(\text{last 12 monthly counts})$$
   $$c_{demand} = \frac{\text{rank} - 1}{N - 1} \quad \text{(average ties; min-max if } N < 5; 0.5 \text{ if } N=1)$$

2. **Trend ($c_{trend}$)**:
   $$c_{trend} = \text{clamp}\left(\frac{g_{low} - g_{min}}{g_{max} - g_{min}}\right)$$
   *(Defaults: $g_{min} = -0.30, g_{max} = +0.30$. Central and optimistic variants use $g_{central}$ and $g_{high}$).*

3. **Pay Yield ($c_{pay}$)**:
   $$\text{pay\_raw} = \frac{p_{50}}{\max(\text{typical\_route\_cost}, \text{cost\_floor})}$$
   $$c_{pay} = \text{percentile\_rank}(\ln(\text{pay\_raw}))$$
   *(Default $\text{cost\_floor} = 50,000$ INR).*

4. **Low Disruption ($c_{disr}$)**:
   $$c_{disr} = 1 - D \quad (D \in [0, 1])$$

5. **Local Demand ($c_{local}$)**:
   $$LQ = \frac{C_{reg} / C_{nat}}{A_{reg} / A_{nat}}$$
   $$c_{local} = \text{clamp}\left(\frac{LQ}{\text{lq\_cap}}\right) \quad (\text{default } \text{lq\_cap} = 2.0)$$
   *(Unavailable if student region is omitted or either regional figure is zero/missing).*

---

## 3. Composite Market Score ($F_{market}$)

$$F_{market} = 100 \times \sum_{k \in \text{Available}} w_k^{used} \cdot c_k$$
Where $w_k^{used} = w_k / \sum_{available} w_i$. Nominal weights:
- Demand level: 0.25
- Trend: 0.30
- Pay yield: 0.20
- Low disruption: 0.15
- Local demand: 0.10

### Honest Uncertainty Display
- $F_{market}$ (pessimistic, uses $g_{low}$)
- $F_{market}^{central}$ (uses $g_{central}$)
- $F_{market}^{optimistic}$ (uses $g_{high}$)

---

## 4. Forecasting Ladder (`forecast.py`)

1. **$\ge 24$ points**: Statsmodels `ETSModel` (additive error, additive damped trend, additive seasonality if $\ge 36$ points), 80% prediction interval.
2. **12–23 points**: OLS on $\ln(\text{count} + 1)$ with 80% observation prediction interval; flagged `"short series"`.
3. **$< 12$ points / fit failure**: `curated_trend` fallback; flagged `"curated estimate, not forecast"`.
4. **Nothing available**: Trend component marked `UNAVAILABLE`.

---

## 5. Risk Proxy (Suggestion for Parent Machine $R_c$)

$$\text{risk\_proxy} = \text{clamp}(0.5 \cdot D + 0.5 \cdot \text{clamp}(\text{volatility} / 0.30))$$
*Note: Using disruption in both $F_{market}$ and $R_c$ double counts it; the engine team must select one.*

---

## 6. Execution Commands

```bash
# Run Market Machine tests
pytest prism/market/tests -v

# Run full PRISM test suite (Parent + Market)
pytest prism/ -v

# Run the Market CLI demo
python prism/market/demo.py
```
