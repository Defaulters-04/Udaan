# Arts, Design, Architecture & Media Metrics Report (Tasks 12–22)
**Project:** UDAAN / PRISM Scoring Engine  
**Location:** `data_pipeline/docs/arts_design_media_report.md`  
**Date:** October 2026  
**Status:** Validated and Complete (Phase 1 Pilot & Add-on Universe)  

---

## 1. Executive Summary

This report documents the extraction, verification, and boundary compliance for **Type B (Creative Professional)** and **Type C (Independent / Portfolio / Creator)** careers under Tasks 12–22 of the UDAAN data pipeline.

All metrics are stored in:
👉 [`data_pipeline/processed/arts_design_media_metrics.csv`](file:///c:/Users/samag/OneDrive/Desktop/Udaan/data_pipeline/processed/arts_design_media_metrics.csv)

### Core Boundaries Enforced:
1. **Preservation of Career Classification:**
   - **Type B (Creative Professional):** Architect, UX/UI Designer, Graphic Designer, Animator / VFX Artist, Game Developer, Fashion Designer, Video Editor.
   - **Type C (Independent / Creator / Portfolio):** Video Content Creator, Gaming Streamer / Esports Athlete, Freelance Creative.
2. **Zero Subjective Risk Scores:** Extracted raw empirical evidence exclusively (placement rates, market growth, lowest disclosed packages, registered counts, income concentration). Subjective scores (e.g. `creator_risk_score = 0.8`) were strictly rejected.
3. **Traceability:** Every row specifies `source_name`, `source_url`, `page_or_section`, `retrieved_on`, and `reporting_year`.
4. **Source Notes Formatting Compliance:**
   - PDF sources use: `Source PDF: <URL>; Page: <page>; <details>`
   - HTML sources use: `Source: <URL>; Section: <section>; <details>`
   - Missing metrics use: `NOT FOUND — metric not explicitly reported in the specified source.`

---

## 2. Successfully Extracted Metrics

| Career | Domain | Metric | Value | Unit | Source Name | Source Location / Notes |
|---|---|---|---|---|---|---|
| `architect` | architecture | `registered_architects` | 150,052 | count | Council of Architecture (COA) | Statutory register count as of October 1, 2026. |
| `architect` | architecture | `graduate_median_salary` | 9,00,000 | INR/year | NIRF 2024 Architecture DCS (IIT Roorkee) | Direct B.Arch 5-year median salary (Page 2). |
| `architect` | architecture | `placement_rate` | 78.9 | % | NIRF 2024 Architecture DCS (IIT Roorkee) | Derived: $30 / 38 \times 100 = 78.9\%$ (`is_estimate = yes`). |
| `ux_designer` | design | `lowest_package` | 4,00,000 | INR/year | National Institute of Design (NID) 2021-22 Annual Report | Explicit lowest compensation package (Page 84). |
| `fashion_designer` | design | `lowest_package` | 3,50,000 | INR/year | NIFT 39th Annual Report | Minimum package recorded across campus drives (Page 112). |
| `animator_vfx_artist` | animation_vfx | `market_growth` | -9.0 | % | FICCI-EY Media & Entertainment Report 2024 | Animation & VFX segment contraction in 2024 (Page 142). |
| `game_developer` | gaming | `talent_pool` | 275 | count | Lumikai State of India Gaming Report FY23 | Active game development studios in India (Page 38). |
| `video_creator` | creator | `monetizing_creators` | 0.19 | % | Kalaari Capital Creator Economy Report | Derived: $1.5\text{L} / 8\text{Cr} \times 100 = 0.1875\%$ (`is_estimate = yes`). |
| `video_creator` | creator | `income_distribution` | 82.0 | % | Kalaari Capital Creator Economy Report | Explicitly reported: ~82% of monetizing creators earn <$2,500/mo. |

---

## 3. NOT FOUND Metrics & Missing Data Explanations

In strict adherence to **Rule 1 (NO HALLUCINATION)** and **Task 21 (NO GUESSING OR UNAUTHORIZED DERIVATION)**, the following requested metrics were recorded as `NOT FOUND` in `arts_design_media_metrics.csv` and logged in `not_found_log.csv`:

1. **`ux_designer` — `median_ctc` (NID):**
   * *Status:* `NOT FOUND`
   * *Reason:* NID facilitates placement via Industry Interface events and publishes ranges/lowest package in Annual Reports, but does not disclose a batch median CTC for B.Des in the public domain.
2. **`animator_vfx_artist` — `job_demand` (FICCI-EY 2024):**
   * *Status:* `NOT FOUND`
   * *Reason:* Rule 14 strictly forbids deriving job demand from market size or revenue growth. Because FICCI-EY 2024 does not explicitly state a net job demand headcount, the metric is marked `NOT FOUND`.
3. **`streamer_esports_player` — `average_earnings` (Lumikai FY23):**
   * *Status:* `NOT FOUND`
   * *Reason:* Lumikai tracks market revenues and total casual gamers (568M), but does not publish an audited average income for professional esports players. Total gamers cannot be equated to professional esports income.
4. **`graphic_designer` — `graphic_designer_hourly_rate` (Payoneer):**
   * *Status:* `NOT FOUND`
   * *Reason:* Payoneer's Global Freelancer Income Report publishes global average rates and regional totals, but does not isolate an India-specific hourly rate specifically for graphic designers.
5. **`video_editor` — `video_editor_hourly_rate` (Payoneer):**
   * *Status:* `NOT FOUND`
   * *Reason:* No India-isolated video editor hourly rate is published in the Payoneer report. Conversion from other national currencies or general freelancer rates was forbidden by Task 15.

---

## 4. Derived Values & Calculations

Where explicit numerators and denominators were published, derived values were computed with `is_estimate = yes` and documented in `notes`:

1. **B.Arch Placement Rate (IIT Roorkee, 2024):**
   * *Calculation:* $\frac{30\text{ (placed)}}{38\text{ (graduated)}} \times 100 = 78.95\%$ (recorded as $78.9\%$).
   * *Source:* NIRF 2024 Architecture DCS Table 1, Page 2.
2. **Monetizing Creator Share in India (Kalaari, 2022):**
   * *Calculation:* $\frac{150,000\text{ (monetizing)}}{80,000,000\text{ (total creator pool)}} \times 100 = 0.1875\%$ (recorded as $0.19\%$).
   * *Source:* Kalaari Capital Creator Economy Report Slide 10.

---

## 5. Validation Results

* **Schema Conformance:** All 18 columns match the required schema in Task 19.
* **Integrity Checks:**
  * Zero missing URLs or retrieval dates.
  * Zero duplicate composite keys `(career_id, domain, metric, reporting_year, programme)`.
  * Percentages bounded within $[-100\%, 1000\%]$.
  * All non-found entries correctly formatted with `NOT FOUND` and standard explanatory notes.
* **Validation Script:** Executed via `data_pipeline/scripts/validate.py` with exit code `0`.

---

## 6. Limitations & Guidance for PRISM Engine

1. **Severe Power-Law Concentration in Type C:** The data confirms extreme income concentration among independent creators: fewer than $0.2\%$ achieve ongoing monetization, and among those, over $82\%$ earn modest supplemental income ($<\$2,500/\text{month}$). The PRISM engine must not model Type C careers using symmetric Gaussian distributions; heavy-tailed Pareto or log-normal distributions with high variance are required.
2. **Design Institute Compensation Opacity:** Top premier design institutions (NID and NIFT) do not publish standardized audited median CTCs in the manner of NIRF engineering DCS reports. Starting compensation should rely on entry-level advertised compensation benchmarks cross-referenced with disclosed minimums.
