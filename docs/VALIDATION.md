# PRISM Engine — Synthetic Personas Validation Report

This report records the read-only validation check of the UDAAN PRISM scoring engine against 12 synthetic student and family personas.

All expectations were defined a priori from common-sense domain principles and data model contracts in `engine/validation/personas.yaml` before running the engine. No engine logic, configuration parameters, or expectations were modified to force test passes.

---

## 1. Executive Summary

- **Total Personas Evaluated:** 12
- **Total Expectations Checked:** 35
- **Passed Expectations:** 30 (85.7%)
- **Failed Expectations:** 5 (14.3%)
- **Exit Code:** `1` (Non-zero due to expectation failures, as required)

---

## 2. Failure Analysis & Diagnostics

For every expectation failure, the table below documents the persona, expectation, observed result, and diagnostic cause assessment:

| Persona | Expectation | Actual Result | Cause Assessment & Rationale |
| :--- | :--- | :--- | :--- |
| `persona_01_creative_student_low_income_medical_family` | Creative careers should dominate top 5 by student fit (`>= 2 of ['ux_designer', 'graphic_designer', 'fine_artist']`) | Found 0 (`['animator_vfx_artist', 'freelance_creative', 'game_developer', 'independent_musician', 'streamer_esports_player']`) | **(c) Wrong expectation**: The full 55-career seed catalogue includes niche digital creative careers with higher raw Artistic/Enterprising benchmark profiles than traditional design tracks. |
| `persona_01_creative_student_low_income_medical_family` | Conflict index should be high due to divergent domain and risk preferences (`Conflict Index >= 40.0`) | `Conflict Index = 35.3` | **(b) Weight/threshold rethinking**: The 4-dimension equal weighting (0.25 each) dilutes the strong domain mismatch (31.2%) and risk gap (45.0%) because time-to-income (0%) and relocation (45%) moderate the composite mean to 35.3%. |
| `persona_02_investigative_numeric_wealthy_aligned` | High tech and analytical careers should dominate student fit (`>= 2 of ['ai_ml_engineer', 'data_scientist', 'software_developer']`) | Found 1: `['ai_ml_engineer']` (Top 5: `['aerospace_engineer', 'ai_ml_engineer', 'biomedical_engineer', 'chemical_engineer', 'civil_engineer']`) | **(c) Wrong expectation**: In the default catalogue, all engineering disciplines share identical baseline cognitive aptitude requirements and domain RIASEC benchmarks, tying their fit scores and pushing data/software outside top 5 alphabetically. |
| `persona_11_type_c_creator_risk_averse_parent` | Creative design pathways lead student fit (`>= 2 of ['graphic_designer', 'fine_artist', 'ux_designer']`) | Found 0 (`['animator_vfx_artist', 'freelance_creative', 'game_developer', 'independent_musician', 'streamer_esports_player']`) | **(c) Wrong expectation**: For high Artistic (0.95) and Enterprising (0.85) creator profiles, independent media careers score higher than studio design careers in the current catalogue. |
| `persona_11_type_c_creator_risk_averse_parent` | Fine artist has large fit_gap (\|Fit - Family\|) reflecting family hesitation (`fit_gap >= 20.0`) | `fit_gap = 6.4` (Fit: 87.0, Family: 80.6) | **(b) Weight/threshold rethinking**: The verified route for `fine_artist` has minimal tuition (INR 36,000), yielding a 100% financial score ($f_{financial} = 1.0$) which overshadows parental domain reservations ($w_{financial} = 0.50$ vs $w_{aspiration} = 0.30$). |

---

## 3. Persona Breakdown Table

| Persona ID | Description | Passed | Failed | Total | Status |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `persona_01_creative_student_low_income_medical_family` | Strong creative interest, low-income family wanting a medical career | 3 | 2 | 5 | 2 FAILED |
| `persona_02_investigative_numeric_wealthy_aligned` | Strong investigative & numeric profile, wealthy aligned family | 3 | 1 | 4 | 1 FAILED |
| `persona_03_undecided_flat_riasec` | Flat, undecided interest profile (`low_signal=True`, neutral score) | 2 | 0 | 2 | **ALL PASSED** |
| `persona_04_high_interest_weak_aptitude_stretch` | High interest but weak aptitude in demanding career (`stretch=True`) | 3 | 0 | 3 | **ALL PASSED** |
| `persona_05_missing_academic_prerequisites` | Missing mandatory subjects and marks band (academic gate blocks) | 2 | 0 | 2 | **ALL PASSED** |
| `persona_06_zero_savings_high_loan_reluctance` | Family savings near zero and high loan reluctance ($G_{fin}$ fails) | 2 | 0 | 2 | **ALL PASSED** |
| `persona_07_fully_aligned_family` | Student and parent fully aligned (conflict index near zero) | 3 | 0 | 3 | **ALL PASSED** |
| `persona_08_fully_opposed_family` | Student and parent opposed on every dimension (very high conflict) | 3 | 0 | 3 | **ALL PASSED** |
| `persona_09_missing_salary_insufficient_data` | Career with missing salary (`status: insufficient_data`, excluded) | 3 | 0 | 3 | **ALL PASSED** |
| `persona_10_scholarship_flips_financial_gate` | Same student as persona 1 with large scholarship ($G_{fin}$ flips to 1) | 3 | 0 | 3 | **ALL PASSED** |
| `persona_11_type_c_creator_risk_averse_parent` | Type C creator interest with risk-averse parent | 1 | 2 | 3 | 2 FAILED |
| `persona_12_compromise_zone_boundary_case` | Boundary case: Fit and Family just above and below cutoff | 2 | 0 | 2 | **ALL PASSED** |
| **TOTAL** | **12 Synthetic Personas** | **30** | **5** | **35** | **5 FAILED (85.7% Pass Rate)** |

---

## 4. Key Behavioral Guarantees Verified

1. **Aptitude Stretch Flag (Fix 3):** Verified in Persona 4. A 40% cognitive deficit triggered `stretch = True` and listed `'logical'` and `'numerical'` deficits, while preserving academic gate clearance (`G_acad = 1`) and non-zero fit score.
2. **Missing Data Handling (Fix 4):** Verified in Persona 9. Unverified entry salary returned `status: insufficient_data`, failed the financial gate, and was excluded from the compromise zone.
3. **Flat Vector Detection (Fix 6):** Verified in Persona 3. A flat RIASEC vector ($\text{std} < 0.02$) correctly triggered `low_signal = True` and returned exactly $50.0$ neutral fit.
4. **Academic Prerequisite Gating:** Verified in Persona 5. Sub-50% marks and missing biology/NEET blocked the academic gate with actionable diagnostics.
5. **Scholarship Impact:** Verified in Persona 10. A grant offset successfully flipped $G_{fin}$ from 0 to 1 for an otherwise unaffordable pathway.
6. **Compromise Zone Cutoff:** Verified in Persona 12. Candidate with $Fit = 53\%$ entered the compromise zone; candidate with $Fit = 47\%$ was excluded.
