# Phase 0: Source Access and Feasibility Audit Report
**Project:** UDAAN / PRISM Scoring Engine  
**Author:** Data Extraction Specialist  
**Location:** `data_pipeline/docs/source_access_report.md`  
**Date:** October 2026  
**Status:** Complete — Awaiting User Approval to Proceed to Phase 1  

---

## 1. Executive Summary & Objective

The **UDAAN Data Pipeline** builds sourced, traceable, and empirically rigorous datasets to power the **PRISM Scoring Engine**. PRISM evaluates careers along two primary dimensions:
1. **Student Fit:** Skills, creative orientation, and role affinity.
2. **Family Viability:** Financial investment, payback horizon, demand trajectory, technological disruption risk, and geographic concentration.

To support Monte Carlo simulations on starting compensation, monthly demand time series, and risk modeling across employment structures (**Type A = Employer-based**, **Type B = Creative Professional**, **Type C = Independent / Creator / Entrepreneurial**), this Phase 0 audit reviews all data sources specified in the pipeline tasks (Tasks 1–11 and Add-on Tasks 12–22).

### Core Boundaries & Audit Rules Enforced:
- **Filesystem Isolation:** All work is confined to `data_pipeline/`. No modifications to `frontend/`, `backend/`, `api/`, `engine/`, or the repository root.
- **Python Environment:** Execution will use `data_pipeline/.venv`.
- **Secrets Management:** Credentials (`ADZUNA_APP_ID`, `ADZUNA_APP_KEY`) reside exclusively in `data_pipeline/.env`. Git exclusion configured in `data_pipeline/.gitignore`.
- **Zero Hallucination & Traceability:** Missing metrics are recorded as `NOT FOUND` and logged in `not_found_log.csv`. Every row requires `source_name`, `source_url`, `page_or_section`, and `retrieved_on`.
- **Prohibited Sources:** Live web scraping of Naukri, LinkedIn, Glassdoor, AmbitionBox, or any portal forbidding automated scraping is strictly omitted.

---

## 2. Comprehensive Source-by-Source Audit

### Task 1: Adzuna India API
* **Portal / Registration:** [developer.adzuna.com](https://developer.adzuna.com/)
* **Access Method:** API Key authentication (`app_id` and `app_key` passed as query parameters). Free developer registration available.
* **Country Support:** Fully supports India via country code path `in` (Base URL: `https://api.adzuna.com/v1/api/jobs/in/`).
* **Endpoints Evaluated:**
  * `search` (`/jobs/in/search/{page}`): Full job listing search by keyword (`what`) and location (`where`). Returns listing count, employer, category, location, and salary ranges.
  * `categories` (`/jobs/in/categories`): Taxonomy of industry categories.
  * `histogram` (`/jobs/in/histogram`): Current distribution of vacancies across salary brackets for a keyword/location query.
  * `history` (`/jobs/in/history`): Historical monthly average advertised salaries.
  * `geodata` (`/jobs/in/geodata`): Geographic vacancy counts by sub-region and city. Recommended as first call to establish macro city distributions.
  * `top_companies` (`/jobs/in/top_companies`): Top hiring employers by volume.
* **Salary Prediction & Jobsworth Flag:**
  * Adzuna operates a dedicated `/jobs/in/jobsworth` salary predictor endpoint.
  * In standard search results, Adzuna provides estimated compensation when employers omit salary figures, identified by the boolean/integer flag **`salary_is_predicted`** (`1` = predicted by Adzuna, `0` = explicit employer stated).
  * The `histogram` endpoint aggregates advertised salaries across active listings; because many Indian job postings lack explicit salary disclosure, the underlying vacancy pool with salary data is smaller than total listings. The pipeline will record `includes_predicted_salaries` accurately based on the API response contract.
* **Rate Limits & Budgeting:**
  * Default free developer tier: 25 requests/minute, 250 requests/day, 1,000 requests/week, 2,500 requests/month.
  * Pilot hard cap: **150 calls** strictly enforced in code.
  * Caching: All raw JSON payloads cached under `data_pipeline/raw/adzuna/` to guarantee deterministic reproduction and prevent duplicate requests.
* **Target Cities:** Bengaluru, Hyderabad, Chennai, Pune, Mumbai, Delhi NCR.
* **Terms of Use:** Permitted for programmatic access using registered API credentials; automated abuse or circumventing limits is prohibited.

---

### Task 2: Naukri JobSpeak Monthly Reports
* **Publisher:** Info Edge (India) Limited.
* **Access Method:** Open public access.
* **Source URLs:**
  * Official PDF Archive: [Info Edge Corporate JobSpeak Archive](https://www.infoedge.in/naukri-jobspeak/)
  * Blog / HTML Summaries: [Naukri Blog - JobSpeak](https://www.naukri.com/blog/jobspeak/)
* **Series Availability:** Monthly releases from January 2023 through the latest available month. Base index established at July 2008 = 1,000.
* **Fields Available:**
  * Overall national hiring index.
  * Sector-wise hiring indices (IT-Software, BFSI, Healthcare, Oil & Gas, Retail, FMCG, Manufacturing).
  * Metro and Tier-2 city indices (Bengaluru, Hyderabad, Chennai, Pune, Mumbai, Delhi-NCR, Kolkata, Ahmedabad).
  * Experience band indices (0-3 years, 4-7 years, 8-12 years, 13-16 years, 16+ years).
  * Emerging tech / AI & ML hiring growth metrics.
* **Restatement Handling:** Info Edge periodically updates methodology or sub-industry classifications (such as the September 2023 recalibration). Per pipeline rules, when historical index values are revised in subsequent reports, the most recent report's value is used, flagged with `restated = yes`, and the specific reporting document is identified in notes.
* **Terms of Use:** Published PDF reports and official blog releases are publicly available for research and analysis. Live scraping of `naukri.com` job postings remains strictly forbidden.

---

### Task 3: WEF Future of Jobs Report 2025
* **Publisher:** World Economic Forum (Geneva).
* **Release Date:** January 7, 2025.
* **Access Method:** Open access download (no paywall or registration required).
* **Source URL:** [WEF Future of Jobs Report 2025](https://www.weforum.org/reports/the-future-of-jobs-report-2025/)
* **File Format:** PDF (200+ pages) and interactive web summary.
* **Fields & Key Metrics:**
  * **Chapter 2 (Employment Outlook):**
    * Global job creation projected (2025–2030): **170 million jobs**.
    * Global job displacement projected (2025–2030): **92 million jobs**.
    * Net global employment change: **+78 million jobs**.
  * **Figure 2.3 (Fastest-Growing & Fastest-Declining Roles):** Visual infographic detailing projected net percentage growth and decline across occupational clusters.
    * Fastest growing: AI & Machine Learning Specialists, Big Data Specialists, FinTech Engineers, Software & Applications Developers, Autonomous & Electric Vehicle Specialists, Environmental Engineers, Security Specialists.
    * Fastest declining: Postal Service Clerks, Bank Tellers, Data Entry Clerks, Administrative Assistants & Executive Secretaries, Cashiers & Ticket Clerks, Printing Workers, Accountants & Auditors.
  * **Data Extraction Rule:** Because Figure 2.3 is an image in the report, numbers extracted via visual examination are marked with `needs_human_check = yes`.
  * **Automation Exposure per Career:** WEF provides technology adoption rates and overall task automation estimates (e.g. share of tasks automated across industries), but **does not publish individual automation exposure scores per specific career title**. Per Rule 1 & Task 3, automation exposure for individual careers will be recorded as `NOT FOUND`.
* **Licence:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0).

---

### Task 4: MoSPI Periodic Labour Force Survey (PLFS)
* **Publisher:** Ministry of Statistics and Programme Implementation (MoSPI), Government of India.
* **Latest Available Release:** **Annual Report 2023–2024** (released September 23, 2024; survey period July 2023 to June 2024), supplemented by recent Quarterly Bulletins for urban metrics.
* **Access Method:** Open Government Data (no login, no fee).
* **Source URLs:** [mospi.gov.in](https://www.mospi.gov.in/) and [microdata.gov.in](https://microdata.gov.in/NADA/).
* **File Format:** Official PDF reports and Excel statistical tables (`.xlsx` / `.xls`).
* **Fields Available:**
  * Labour Force Participation Rate (LFPR) by State/UT.
  * Worker Population Ratio (WPR) by State/UT.
  * Unemployment Rate (UR) by State/UT (National overall: 3.2% in Usual Status ps+ss for 2023–24).
  * Disaggregation across Usual Status (ps+ss) and Current Weekly Status (CWS), rural/urban sectors, and male/female categories.
* **Licence:** Open Government Data (OGD) Licence India.

---

### Task 5: NASSCOM Strategic Review & NCS Portal / MoLE
* **NASSCOM Strategic Review:**
  * **Access Status:** The complete annual research volumes (e.g., *Strategic Review 2024: Rewiring Growth*, *Strategic Review 2025: Beyond Disruption*) are gated behind a paid membership paywall on the NASSCOM Insights portal.
  * **Publicly Available Information:** NASSCOM publishes extensive official executive summaries, press releases, and community articles during the annual NASSCOM Technology & Leadership Forum (NTLF).
  * **Sourced Public Metrics:**
    * Tech industry revenue ($282.6 Billion FY25E; $250+ Billion FY24).
    * Total direct tech employment (5.4M+ workforce) and net hiring figures.
    * GCC (Global Capability Center) market footprint and AI patent / talent pool growth.
  * **Audit Finding:** Granular career-level compensation tables from NASSCOM are proprietary and behind the paywall. Where specific career-level figures are gated, they will be logged as `NOT FOUND` rather than extracted from unauthorized re-uploads.
* **National Career Service (NCS) Portal & Ministry of Labour (MoLE):**
  * **Access Status:** Open public access via [ncs.gov.in](https://www.ncs.gov.in/).
  * **Data Available:** Public NCS Dashboard and downloadable Employment Exchange Statistics reports (annual publications through 2023/2024).
  * **Fields:** Registered job seekers (over 2.89 crore active), active vacancies (17.68 lakh), state-wise registrations, and sector-wise demand postings.

---

### Task 6: Type C Industry & Income Data (Creator Economy & Gaming/Esports)
* **Scope:** Independent, portfolio, and creator careers where traditional employer listings and wage boards do not apply.
* **Reports Audited:**
  1. **Kalaari Capital — India Creator Economy Report:**
     * *Format & Access:* Open slide deck/report published on [kalaari.com](https://kalaari.com/).
     * *Available Metrics:* Total creator universe (~80 million creators and knowledge professionals); monetizing creators (~1.5 lakh, or approx. 0.2%); income distribution brackets ($200–$2,500/month for mainstream professional creators; top <1% with >1M followers earning $2,500–$65,000/month).
     * *Limitations:* Does not define an official "living wage" metric; per prompt rules, living wage will not be inferred and is marked `NOT FOUND`.
  2. **Kofluence — Influencer Marketing Reports ("Decoding Influence"):**
     * *Format & Access:* Open download via [kofluence.com](https://kofluence.com/).
     * *Available Metrics:* Influencer marketing market size (projected ₹4,500–5,000 Crore by 2027, ~22% CAGR), tier-2/3 regional creator engagement, brand partnership models (76.6% partnership ads, 62.1% long-term contracts).
  3. **Oxford Economics (commissioned by YouTube) — YouTube Economic Impact India:**
     * *Format & Access:* Open PDF summary on [oxfordeconomics.com](https://www.oxfordeconomics.com/) / YouTube official blog.
     * *Available Metrics:* YouTube creative ecosystem contributed over **₹18,000 Crore to Indian GDP**; supported **9.6 lakh full-time equivalent (FTE) jobs**.
  4. **Lumikai — State of India Gaming Reports (FY23, FY24):**
     * *Format & Access:* Open digital report published by Lumikai in collaboration with Google.
     * *Available Metrics:* Market valuation ($3.1 Billion growing to projected $7.5 Billion by FY28); total gamers (568 million); game development studio count (growing from 15 in 2009 to 275+).
     * *Limitations:* Gaming user counts are strictly kept separate from professional developers and esports athletes. If professional average earnings are not published, they will be logged as `NOT FOUND`.
  5. **FICCI-EY Media & Entertainment Reports (2023, 2024, 2025 editions):**
     * *Format & Access:* Available via [ficci.in](https://ficci.in/) and [ey.com](https://www.ey.com/).
     * *Available Metrics:* Total M&E valuation (₹2.78 Trillion in 2025; ₹2.5 Trillion in 2024); Animation & VFX market movements (-9% contraction in 2024; VFX specifically -14%); online gaming segment dynamics.
  6. **PwC Global Entertainment & Media Outlook:**
     * *Format & Access:* Open India executive summary. Macro segment forecasts.
* **Vendor & Platform Bias Labeling:** Kalaari and Lumikai are venture capital funds; Kofluence is an influencer agency; Oxford Economics was commissioned by YouTube. Every extracted row from these sources will be explicitly labeled in `notes` with `source_type = report` or `survey` and a note stating the commercial/sponsor relationship.

---

### Task 7: Salary Bands (INR LPA) & Histogram Derivation
* **Methodology:** For employer-based careers (Type A and Type B), starting compensation percentiles ($p10, p25, p50, p75, p90$) will be derived from Adzuna salary histogram buckets using piecewise cumulative frequency interpolation.
* **Pipeline Rule Compliance:**
  * Derived percentiles are marked with `is_estimate = yes` and `source_type = derived`.
  * The exact interpolation formula and frequency counts are documented in the `notes` column.
  * Where Adzuna histograms have fewer than 10 total vacancies with explicit salary disclosure for a specific keyword, derivation will not be attempted and values will be recorded as `NOT FOUND`.
  * No web scraping of LinkedIn, Glassdoor, AmbitionBox, or Naukri.

---

### Task 8: NIRF Master Data (2016–2025) & Kaggle Audit
* **Audit of Kaggle NIRF Datasets:**
  * Several Kaggle datasets exist (e.g., *NIRF Rankings Dataset 2016–2025*, *NIRF Indian University Rank*, *NIRF 2023 India National Institutional Ranking*), published under CC0 / CC BY 4.0 licenses.
  * **Critical Audit Finding:** Kaggle datasets almost universally contain only the aggregate ranking tables and parameter scores (**TLR, RPC, GO, OI, PR, Total Score**). They **do not contain** the detailed Data Capturing System (DCS) tables containing undergraduate and postgraduate sanctioned intake, admitted students, graduation numbers, placed students, students pursuing higher studies, and median salaries.
* **Official NIRF Solution:**
  * The official NIRF portal ([nirfindia.org](https://www.nirfindia.org/)) hosts the primary, unaudited Data Capturing System (DCS) reports for every ranked institution across Engineering, Medical, Architecture, and Overall categories.
  * These reports are accessible directly via the "More Details | | DCS" links alongside each institution in the annual ranking lists from 2016 through 2024/2025.
* **Nature of Data & Integrity Rules:**
  * NIRF figures represent institute self-reported, unaudited declarations.
  * The definition of "placed" is not standardized across institutions.
  * In `college_outcomes.csv`, `source_type` will strictly be set to `self_reported`.
  * Discipline or national medians will never be computed by averaging institution medians.

---

### Task 9: AICTE Know Your College / AICTE Dashboard
* **Portal:** AICTE Web Portal & Facilities Dashboard ([facilities.aicte-india.org/dashboard/](https://facilities.aicte-india.org/dashboard/pages/angulardashboard.php)).
* **Access Method:** Open public search query.
* **Export Format Audit:**
  * The public-facing portal does not offer a bulk "one-click" CSV or Excel export for all institutions across India.
  * Institute data (approved intake, specific approved programmes, state, city, institution type) is rendered as dynamic HTML tables and individual downloadable PDF Extension of Approval (EOA) letters.
  * Institutional aggregated statistics are published annually in the official *AICTE Approval Process Handbook (APH) Statistics*.
* **Pipeline Strategy:** For target colleges, approved intake and programme approvals will be extracted from the official approval dashboard / EOA notices and cross-referenced with NIRF DCS intake declarations.

---

### Task 10: Entrance Cutoffs (Latest Academic Year)
* **1. JoSAA (Joint Seat Allocation Authority):**
  * Portal: [josaa.admissions.nic.in](https://josaa.admissions.nic.in/)
  * Availability: Full Opening and Closing Ranks (OR-CR) for all 5–6 counselling rounds for IITs, NITs, IIITs, and GFTIs across academic years 2023, 2024, and historical cycles.
  * Seat Categories: Exact reservation categories preserved without merging:
    * `OPEN` (CRL — Common Rank List)
    * `GEN-EWS` (Category Rank)
    * `OBC-NCL` (Category Rank)
    * `SC` (Category Rank)
    * `ST` (Category Rank)
    * PwD subcategories preserved verbatim.
* **2. TNEA (Tamil Nadu Engineering Admissions):**
  * Portal: [tneaonline.org](https://www.tneaonline.org/) (Directorate of Technical Education, Chennai).
  * Availability: College-wise and branch-wise closing cutoffs (based on aggregate marks out of 200) across community categories (`OC`, `BC`, `BCM`, `MBC/DNC`, `SC`, `SCA`, `ST`).
* **3. WBJEE (West Bengal Joint Entrance Examination):**
  * Portal: [wbjeeb.nic.in](https://wbjeeb.nic.in/)
  * Availability: Round-wise opening and closing ranks for West Bengal state universities and private engineering colleges. Categories (`OPEN`, `TFW`, `SC`, `ST`, `OBC-A`, `OBC-B`, Home State vs All India) preserved.
* **4. Medical (NEET UG / MBBS):**
  * Portals: Medical Counselling Committee ([mcc.nic.in](https://mcc.nic.in/)) for All India Quota (AIQ) 15% and central/deemed universities; National Medical Commission ([nmc.org.in](https://www.nmc.org.in/)) for approved college lists and annual intake capacity.
  * Categories: `OPEN`, `EWS`, `OBC`, `SC`, `ST` All India closing NEET UG ranks.

---

### Task 11: Institutional Fees & Target Colleges
* **Sources:** Direct fee notifications from official institute portals, finance circulars, and official state counselling brochures (e.g. TNEA / WBJEE approved fee structure notifications).
* **Format & Detail:**
  * Academic year of applicability clearly stated.
  * Separated into Annual Tuition, Hostel & Mess Charges, and Other Mandatory Fees.
  * If a fee schedule cannot be verified from an official publication, recorded as `NOT FOUND`.

---

## 3. Add-on Tasks Audit: Arts, Design, Architecture & Media (Tasks 12–22)

### Task 12: Architecture (COA + NIRF Architecture)
* **Council of Architecture (COA):**
  * Official Website: [coa.gov.in](https://www.coa.gov.in/)
  * Status: COA maintains a centralized statutory register of architects under the Architects Act, 1972.
  * Latest Available Metric: Total registered architects in India = **150,052** (as of October 1, 2026 registration statistics).
* **NIRF Architecture Category:**
  * Official Website: [nirfindia.org](https://www.nirfindia.org/) (Architecture category rankings and DCS files).
  * Metrics Available: B.Arch median salary (explicitly reported in DCS UG 5-Year Program table), graduating count, and placed count.
  * Calculation Rule: Placement percentage is computed as $(\text{placed} / \text{graduated}) \times 100$ only when numerator and denominator are explicitly provided. Set `is_estimate = yes` and document calculation in `notes`. Never infer B.Arch salary from M.Arch or other programmes.

---

### Task 13: Design (NID + NIFT)
* **National Institute of Design (NID):**
  * Official Website: [nid.edu](https://www.nid.edu/)
  * Audit Findings: NID facilitates placement through its Industry Interface events. Consolidated median CTC is **not** publicly published as a standard metric in public brochures. Annual Reports report highest package (e.g. ₹30 LPA in 2021–22) and lowest disclosed package (e.g. ₹4 LPA), but omit median CTC.
  * Pipeline Rule: Per Task 13, because average or highest CTC cannot be substituted for median CTC, **median CTC will be recorded as `NOT FOUND`**, while explicitly reported lowest package is preserved.
* **National Institute of Fashion Technology (NIFT):**
  * Official Website: [nift.ac.in](https://nift.ac.in/)
  * Audit Findings: NIFT publishes centralized placement brochures and Annual Reports reporting average package (e.g., ~₹5.5 LPA across campuses) and campus-specific recruitment drives. Median CTC across B.Des programmes is not uniformly disclosed in the public domain.
  * Pipeline Rule: Median CTC marked as `NOT FOUND` where not explicitly stated; programme (B.Des vs M.Des) and campus distinctions strictly preserved.

---

### Task 14: Media, Animation, VFX & Gaming
* **FICCI-EY Media & Entertainment Report:**
  * Focus: Animation, VFX, AVGC, and Online Gaming segments.
  * Available Metrics: YoY growth rates (Animation & VFX contracted 9% in 2024, VFX contracted 14%; overall M&E grew 3.3% in 2024 to ₹2.5T and 9% in 2025 to ₹2.78T).
  * Strict Boundary: Employment / job demand will be extracted **only if explicitly reported** as an employment figure. Job demand will **never** be derived from market size, revenue, or growth rate. If not explicitly published: `NOT FOUND`.
* **Lumikai Gaming Report:**
  * Available Metrics: Gaming market size ($3.1B to $7.5B FY28), developer studio count (275+).
  * Strict Boundary: Total gamers (568M) will **never** be equated to game developers or esports professionals. Professional player counts and developer average earnings will only be extracted if explicitly defined; otherwise logged as `NOT FOUND`.

---

### Task 15: Freelance & Creator Economy
* **Payoneer Freelancer Report:**
  * Official Website: [payoneer.com](https://www.payoneer.com/) (Global Freelancer Income Report).
  * Audit Findings: Payoneer publishes global average hourly rates (e.g. $28/hr overall; $20–$22/hr in graphic design globally) and regional participation shares. Payoneer rarely isolates a specific, statistically robust hourly rate for India exclusively broken down for *graphic designers* or *video editors*.
  * Pipeline Rule: Hourly rates will not be calculated from annual income or converted from global averages. If an India-specific, discipline-isolated figure is not explicitly reported in Payoneer's publication, it will be recorded as `NOT FOUND`.
* **Kalaari Creator Economy Report:**
  * Available Metrics: Exact income brackets ($200–$2,500/month; <1% >$2,500/month; 0.2% monetizing).
  * Strict Boundary: The term "living wage" will not be self-defined. The exact reported income distribution will be recorded, and any living wage percentage is marked `NOT FOUND`.

---

### Tasks 16–22: Risk Evidence, Career Classification & Integrity Rules
* **No Subjective Risk Scores:** The pipeline will extract only raw evidence (hourly rates, placement rates, median CTCs, income concentration, market growth). No arbitrary numbers (e.g., `risk_score = 0.8`) will be generated.
* **Preservation of Career Types:**
  * **Type B (Creative Professional):** Architect, UX Designer, Graphic Designer, Animator / VFX Artist, Game Developer, Industrial Designer, Video Editor.
  * **Type C (Independent / Portfolio / Creator):** Content Creator, Streamer, Musician, Freelancer.
* **Output Artifacts for Add-on:**
  * Processed data: `data_pipeline/processed/arts_design_media_metrics.csv`
  * Add-on documentation: `data_pipeline/docs/arts_design_media_report.md`
  * Format requirement for PDF sources in notes: `Source PDF: <direct PDF URL>; Page: <page number>; <specific description>`

---

## 4. Proposed Target College List (Task 11)

Per Task 11 requirements, the target college list must comprise approximately **30 representative institutions** covering:
1. Top NIRF Engineering Institutes (National flagships).
2. State Government Engineering Colleges in Tamil Nadu (TNEA counselling cutoffs).
3. State Government Engineering Colleges in West Bengal (WBJEE counselling cutoffs).
4. Large Private Universities (High intake, multi-campus).
5. Top Medical Colleges (MBBS, MCC / NEET UG counselling cutoffs and NMC approved intake).

The proposed target list of **32 institutions** is detailed below for user review and approval:

| # | Institute Name | Short Name | Category | State | City | Primary Admission Channel / Authority | NIRF Ranking / Tier |
|---|---|---|---|---|---|---|---|
| 1 | Indian Institute of Technology Madras | IIT Madras | Top NIRF Engg | Tamil Nadu | Chennai | JoSAA (JEE Advanced) | NIRF Engg #1 |
| 2 | Indian Institute of Technology Delhi | IIT Delhi | Top NIRF Engg | Delhi | New Delhi | JoSAA (JEE Advanced) | NIRF Engg #2 |
| 3 | Indian Institute of Technology Bombay | IIT Bombay | Top NIRF Engg | Maharashtra | Mumbai | JoSAA (JEE Advanced) | NIRF Engg #3 |
| 4 | Indian Institute of Technology Kanpur | IIT Kanpur | Top NIRF Engg | Uttar Pradesh | Kanpur | JoSAA (JEE Advanced) | NIRF Engg #4 |
| 5 | Indian Institute of Technology Kharagpur | IIT Kharagpur | Top NIRF Engg | West Bengal | Kharagpur | JoSAA (JEE Advanced) | NIRF Engg #5 |
| 6 | Indian Institute of Technology Roorkee | IIT Roorkee | Top NIRF Engg | Uttarakhand | Roorkee | JoSAA (JEE Advanced) | NIRF Engg #6 |
| 7 | National Institute of Technology Tiruchirappalli | NIT Trichy | Top NIRF Engg (NIT) | Tamil Nadu | Tiruchirappalli | JoSAA (JEE Main) | NIRF Engg #9 |
| 8 | National Institute of Technology Karnataka | NIT Surathkal | Top NIRF Engg (NIT) | Karnataka | Surathkal | JoSAA (JEE Main) | NIRF Engg #12 |
| 9 | International Institute of Information Technology Hyderabad | IIIT Hyderabad | Top Engg (IIIT) | Telangana | Hyderabad | Institute Portal (JEE Main / UGEE) | Premier Tech Flagship |
| 10 | Birla Institute of Technology and Science, Pilani | BITS Pilani | Top Deemed Engg | Rajasthan | Pilani | BITSAT | Premier Private Flagship |
| 11 | College of Engineering, Guindy (Anna University) | CEG Anna Univ | State Govt Engg (TN) | Tamil Nadu | Chennai | TNEA (DoTE Tamil Nadu) | Premier TN State Govt |
| 12 | Madras Institute of Technology (Anna University) | MIT Anna Univ | State Govt Engg (TN) | Tamil Nadu | Chennai | TNEA (DoTE Tamil Nadu) | Premier TN State Govt |
| 13 | Government College of Technology, Coimbatore | GCT Coimbatore | State Govt Engg (TN) | Tamil Nadu | Coimbatore | TNEA (DoTE Tamil Nadu) | Major TN State Govt |
| 14 | PSG College of Technology | PSG Tech | Govt-Aided / Autonomous (TN) | Tamil Nadu | Coimbatore | TNEA (DoTE Tamil Nadu) | Top Aided TN Autonomous |
| 15 | Thiagarajar College of Engineering | TCE Madurai | Govt-Aided / Autonomous (TN) | Tamil Nadu | Madurai | TNEA (DoTE Tamil Nadu) | Top Aided TN Autonomous |
| 16 | Jadavpur University (Faculty of Engg & Tech) | Jadavpur Univ | State Govt Engg (WB) | West Bengal | Kolkata | WBJEE (WBJEEB) | NIRF Engg #10, Top WB State |
| 17 | University of Calcutta (Faculty of Tech) | Calcutta Univ | State Govt Engg (WB) | West Bengal | Kolkata | WBJEE (WBJEEB) | Top WB State University |
| 18 | Kalyani Government Engineering College | KGEC | State Govt Engg (WB) | West Bengal | Kalyani, Nadia | WBJEE (WBJEEB) | Premier WB State Govt College |
| 19 | Jalpaiguri Government Engineering College | JGEC | State Govt Engg (WB) | West Bengal | Jalpaiguri | WBJEE (WBJEEB) | Premier WB State Govt College |
| 20 | Govt College of Engineering and Ceramic Technology | GCECT | State Govt Engg (WB) | West Bengal | Kolkata | WBJEE (WBJEEB) | Specialized WB State Govt |
| 21 | Vellore Institute of Technology | VIT Vellore | Large Private Univ | Tamil Nadu | Vellore | VITEEE | NIRF Engg #11, High Intake |
| 22 | SRM Institute of Science and Technology | SRMIST | Large Private Univ | Tamil Nadu | Kattankulathur | SRMJEEE | NIRF Engg Top 20, High Intake |
| 23 | Thapar Institute of Engineering and Technology | Thapar Univ | Large Private Univ | Punjab | Patiala | JEE Main / TIET Counselling | NIRF Engg Top 25 |
| 24 | Manipal Institute of Technology (MAHE) | MIT Manipal | Large Private Univ | Karnataka | Manipal | MET (MAHE) | NIRF Engg Top 60 |
| 25 | Amrita Vishwa Vidyapeetham | Amrita Univ | Large Private Univ | Tamil Nadu | Coimbatore | AEEE / JEE Main | NIRF Overall Top 10 |
| 26 | Shiv Nadar University | SNU | Large Private Univ | Uttar Pradesh | Greater Noida | SNUSAT / JEE Main | Premier Research Private |
| 27 | All India Institute of Medical Sciences, New Delhi | AIIMS New Delhi | Top Medical | Delhi | New Delhi | MCC (NEET UG) | NIRF Medical #1 |
| 28 | Christian Medical College, Vellore | CMC Vellore | Top Medical (Private/Trust) | Tamil Nadu | Vellore | MCC / TN State (NEET UG) | NIRF Medical #3 |
| 29 | Madras Medical College | MMC Chennai | State Govt Medical (TN) | Tamil Nadu | Chennai | MCC AIQ / TN State (NEET UG) | NIRF Medical Top 15 |
| 30 | Medical College Kolkata (Calcutta Medical College) | CMC Kolkata | State Govt Medical (WB) | West Bengal | Kolkata | MCC AIQ / WBMCC (NEET UG) | Historic WB State GMC |
| 31 | King George's Medical University | KGMU | State Govt Medical (UP) | Uttar Pradesh | Lucknow | MCC AIQ / UP DGME (NEET UG) | NIRF Medical Top 12 |
| 32 | Kasturba Medical College, Manipal (MAHE) | KMC Manipal | Deemed Medical | Karnataka | Manipal | MCC Deemed (NEET UG) | NIRF Medical Top 10 |

---

## 5. Input Files Audit & Pre-Phase 1 Prerequisites

### Workspace Audit of Config Files:
1. `data_pipeline/config/careers_seed.csv`:
   - **Current State:** The root repository file `careers_seed.csv` exists but currently has a file size of **0 bytes** (empty).
   - **Requirement for Phase 1:** Must contain the 45 career definitions, their type (`A`, `B`, `C`), and suggested Adzuna search keywords.
2. `data_pipeline/config/prism_market_data_starter.xlsx`:
   - **Current State:** File is not currently present in the repository.
   - **Requirement for Phase 1:** Sourced dataset of 52 starter rows to be used as a cross-checking benchmark against newly extracted signals.
3. `data_pipeline/.env`:
   - **Requirement:** User must populate `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `data_pipeline/.env` (using `data_pipeline/.env.example` as a template).

---

## 6. Phase 0 Audit Summary Matrix

| Task | Source Name | Public Access | Authentication / Cost | Formats | Anticipated "NOT FOUND" Metrics |
|---|---|---|---|---|---|
| 1 | Adzuna India API | Yes | Free Developer API Key | JSON | Metrics where advertised salary sample is insufficient (<10 listings) |
| 2 | Naukri JobSpeak | Yes | Free / Public | PDF, HTML | Hyperlocal / campus placement data (excluded by methodology) |
| 3 | WEF Future of Jobs 2025 | Yes | Free / Public | PDF, Web | Individual per-career automation exposure scores |
| 4 | MoSPI PLFS (2023-24) | Yes | Free / Public | PDF, Excel | Company-level or granular career-specific salary data |
| 5 | NASSCOM Strategic Review | Partial (Executive summary only) | Full report behind paywall | PDF, Web articles | Proprietary salary compensation tables behind member paywall |
| 5 | NCS Portal (MoLE) | Yes | Free / Public | Web Dashboard, PDF | Private sector wage microdata |
| 6 | Kalaari Creator Economy | Yes | Free / Public | PDF / Slides | Specific "living wage" metric (not defined by Kalaari) |
| 6 | Lumikai Gaming | Yes | Free / Public | PDF / Slides | Individual game developer salaries (unless explicitly published) |
| 6 | FICCI-EY M&E | Yes | Free / Public | PDF | Job demand derived from market size (forbidden by rule) |
| 7 | Adzuna Salary Bands | Yes | Free Developer Key | Derived from JSON | Careers with insufficient salary postings (<10) |
| 8 | NIRF Master Data | Yes | Free / Public | PDF, Web | Official institute audited wage data (data is self-reported) |
| 9 | AICTE Dashboard | Yes | Free / Public | Web HTML, PDF | Bulk CSV download for all institutes simultaneously |
| 10 | JoSAA / TNEA / WBJEE / MCC | Yes | Free / Public | Web HTML, PDF | Non-standard or merged seat categories |
| 11 | Institute & Counselling Fees | Yes | Free / Public | PDF Circulars | Institutes lacking published annual fee breakdowns |
| 12 | COA Registered Architects | Yes | Free / Public | Web Statistics | Individual firm revenue |
| 13 | NID Placements | Partial | Annual Reports Public | PDF | Official batch-wide median CTC for B.Des (not disclosed) |
| 13 | NIFT Placements | Partial | Annual Reports Public | PDF | Official batch-wide median CTC for B.Des (average CTC is reported) |
| 14 | AVGC & Gaming Job Demand | Partial | Free / Public | PDF | AVGC job demand (unless explicitly published in text) |
| 15 | Payoneer Freelancers | Partial | Free / Public | PDF | India-specific graphic designer / video editor isolated hourly rates |

---

## 7. Checkpoint & Recommended Action

Phase 0 Source Audit is **complete**. No extraction or code execution outside audit documentation has been performed.

### Action Items for User Review:
1. **Review and approve this Phase 0 Source Access Report.**
2. **Review and approve the Proposed Target College List (32 institutions across 5 categories in Section 4).**
3. **Populate `data_pipeline/config/careers_seed.csv` and place `prism_market_data_starter.xlsx` into `data_pipeline/config/`.**
4. **Populate `data_pipeline/.env` with your Adzuna API credentials.**
5. **Approve moving to Phase 1 (Pilot extraction for the 6 pilot careers and 6 cities).**
