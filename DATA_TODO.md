# DATA_TODO: Manual Data Verification & Collection Guide

> **Strict Rule**: In accordance with PRISM Engine governance, no synthetic figures, unverified heuristics, or memory-recalled data are permitted. All entries below are currently stored as `NOT FOUND` / `None`. A human researcher must visit the cited official pages, locate the exact figures, and record `source_url`, `page_or_section`, and `retrieved_on` (ISO date).

---

## 1. Salary Band Percentiles (p10 / p90) & Missing Core Salaries

The PRISM Engine's Monte Carlo simulation (`payback_range`) requires both `p10` and `p90` salary percentiles to fit the lognormal distribution ($z = 1.2816$). When either is missing, payback range computation returns `None`.

| Career ID | Field | Current Value | Recommended Official Source | Verification Target / Section |
|:---|:---|:---:|:---|:---|
| `software_developer` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NIRF India IIT Bombay DCS](https://www.nirfindia.org/2024/Declaration/Agreement/DCS/IR-E-U-0456.pdf) / [NASSCOM Insights](https://community.nasscom.in/) | Locate graduate placement distribution percentiles (25th/75th or minimum/maximum salary bands). |
| `cybersecurity_analyst`| `p10_salary`, `p90_salary` | `NOT FOUND` | [NIELIT Recruitment Notifications](https://www.nielit.gov.in/) / [MeitY Pay Scale Gazette](https://www.meity.gov.in/) | Scientist 'B' (Level 10) starting basic pay + DA/HRA entry vs post-probation steps. |
| `mechanical_engineer` | `p10_salary`, `p90_salary` | `NOT FOUND` | [UPSC ESE Notification](https://upsc.gov.in/) / [IOCL / BHEL Recruitment Gazette](https://iocl.com/) | Executive Engineer Grade E2 entry level pay scale vs minimum/maximum stipend. |
| `civil_engineer` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NIRF India IIT Bombay DCS](https://www.nirfindia.org/2024/Declaration/Agreement/DCS/IR-E-U-0306.pdf) / [CPWD Pay Rules](https://cpwd.gov.in/) | Assistant Executive Engineer Level 10 pay band vs private construction firm placement range. |
| `doctor_mbbs` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NMC Regulations](https://www.nmc.org.in/) / [AIIMS Senior Residency Gazette](https://www.aiims.edu/) | Non-academic junior resident / Medical Officer Level 10 entry pay scale across state cadres. |
| `nursing_officer` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NORCET Official Prospectus](https://norcet7.aiimsexams.ac.in/) | Pay Level 7 (₹44,900–₹1,42,400) Grade Pay ₹4,600: starting gross salary including allowance variants. |
| `biomedical_engineer` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NIRF MAHE Manipal DCS](https://www.nirfindia.org/2024/Declaration/Agreement/DCS/IR-E-U-0439.pdf) / [SCTIMST Recruitment](https://www.sctimst.ac.in/) | Biomedical engineering graduate placement percentiles in hospital/medical device sectors. |
| `chartered_accountant`| `p10_salary`, `p90_salary` | `NOT FOUND` | [ICAI Campus Placement Report](https://cmib.icai.org/) | Semi-annual ICAI Campus Placement Committee statistical bulletin (p10/p90 CTC range). |
| `financial_analyst` | `p50_salary`, `p10`, `p90` | `NOT FOUND` | [SEBI Grade A Officer Notification](https://www.sebi.gov.in/) / [RBI Grade B Gazette](https://www.rbi.org.in/) | Officer Grade A basic pay + allowances (starting CTC) or campus hiring reports from JBIMS/NSE. |
| `management_consultant`| `p50_salary`, `p10`, `p90`| `NOT FOUND` | [IIM Ahmedabad Placement Report](https://www.iima.ac.in/) (IPRS Audited) | Audited IPRS management consulting domestic salary distribution. |
| `industrial_designer` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NID Placement Cell Report](https://www.nid.edu/) / [Ministry of MSME Design Scheme](https://msme.gov.in/) | B.Des Industrial/Product design graduate entry salary distribution. |
| `ux_designer` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NIRF IDC IIT Bombay DCS](https://www.nirfindia.org/2024/Declaration/Agreement/DCS/IR-O-U-0306.pdf) | IDC Interaction Design placement median and interquartile ranges. |
| `lawyer_corporate` | `p10_salary`, `p90_salary` | `NOT FOUND` | [NLU Consortium Placement Audits](https://consortiumofnlus.ac.in/) / [PSU Law Officer Scale](https://iocl.com/) | Corporate associate entry level retainer vs PSU Junior Law Officer Level 10 pay. |
| `economist` | `p50_salary`, `p10`, `p90` | `NOT FOUND` | [Indian Economic Service (IES) Gazette](https://upsc.gov.in/) / [Delhi School of Economics Placement](http://www.econdse.org/) | Junior Time Scale (JTS) Level 10 starting salary or DSE MA Economics placement summary. |
| `historian` | `p50_salary`, `p10`, `p90` | `NOT FOUND` | [ICHR Research Grants](https://ichr.ac.in/) / [UGC NET Assistant Professor Scales](https://www.ugc.gov.in/) | Assistant Professor Level 10 starting basic pay (Academic Level 10, 7th CPC). |
| `data_scientist` | `p10_salary`, `p90_salary` | `NOT FOUND` | [DRDO RAC Scientist 'B' Scale](https://rac.gov.in/) / [ISI Placement Brochure](https://www.isical.ac.in/) | Scientist 'B' Grade entry pay vs M.Stat/B.Stat placement distribution percentiles. |
| `environmental_scientist`| `p50_salary`, `p10`, `p90`| `NOT FOUND` | [CPCB Scientist 'B' Notification](https://cpcb.nic.in/) / [ICFRE Research Cadre](https://icfre.gov.in/) | Central Pollution Control Board Scientist 'B' pay scale Level 10. |
| `journalist` | `p50_salary`, `p10`, `p90` | `NOT FOUND` | [Prasar Bharati Recruitment Gazette](https://prasarbharati.gov.in/) / [IIMC Placement Report](https://iimc.gov.in/) | Sub-Editor / Junior Reporter starting scale in public broadcasting or print/digital media. |

---

## 2. Route Living Expenses (Hostel & Mess)

The following routes currently have `cost_status = "partial"` because living costs were not published on official prospectus pages. The engine scores them using known fees as a lower bound (`is_lower_bound = True`).

| Route ID | Institution | Missing Field(s) | Official Portal to Check | Instructions for Human Data Collector |
|:---|:---|:---|:---|:---|
| `route_sw_ju` | Jadavpur University | `hostel_fee_total`, `mess_fee_total` | [Jadavpur Univ Hostels Portal](http://www.jaduniv.edu.in/) | Check Dean of Students hostel seat rent and mess establishment fee circular for engineering hostel. |
| `route_sw_ceg` | CEG Anna University | `hostel_fee_total`, `mess_fee_total` | [Anna Univ Hostel Office](https://www.annauniv.edu/hostel/) | Download CEG Hostel Executive Warden fee circular (Block caution deposit, mess advance, room rent). |
| `route_cyber_ceg` | CEG Anna University | `hostel_fee_total`, `mess_fee_total` | [Anna Univ Hostel Office](https://www.annauniv.edu/hostel/) | Check room rent + dining charges for 4-year engineering stay. |
| `route_cyber_nfsu` | NFSU Gandhinagar | `hostel_fee_total`, `mess_fee_total` | [NFSU Campus Hostel](https://beta.nfsu.ac.in/) | Locate hostel accommodation charges for Gandhinagar campus B.Tech-M.Tech integrated programs. |
| `route_mech_gct` | GCT Coimbatore | `hostel_fee_total`, `mess_fee_total` | [GCT Hostels Page](https://gct.ac.in/) | Check Warden circular for government engineering hostel boarding & lodging charges. |
| `route_mech_cpt` | CPT Chennai | `hostel_fee_total`, `mess_fee_total` | [CPT Chennai Office](http://cptchennai.ac.in/) | Check polytechnic student hostel fee rules under Tamil Nadu DOTE. |
| `route_ce_ceg` | CEG Anna University | `hostel_fee_total`, `mess_fee_total` | [Anna Univ Hostel Office](https://www.annauniv.edu/hostel/) | Check room rent + mess advance for civil engineering students. |
| `route_med_aiims` | AIIMS New Delhi | `mess_fee_total` | [AIIMS Hostel Regulations](https://www.aiims.edu/) | Room rent is verified (₹990); verify mess deposit and monthly billing in AIIMS student handbook. |
| `route_med_mmc` | Madras Medical College | `hostel_fee_total`, `mess_fee_total` | [TN Medical Selection](https://tnmedicalselection.net/) | Check MMC hostel accommodation circular for undergraduate MBBS students. |
| `route_nurse_aiims` | AIIMS New Delhi | `hostel_fee_total`, `mess_fee_total` | [AIIMS Exams Hostel Rules](https://norcet7.aiimsexams.ac.in/) | AIIMS B.Sc Nursing hostel accommodation charges and mess subscription fee. |
| `route_bme_ceg` | CEG Anna University | `hostel_fee_total`, `mess_fee_total` | [Anna Univ Hostel Office](https://www.annauniv.edu/hostel/) | CEG hostel annual charges for biomedical engineering students. |
| `route_bme_ceg_govt`| CEG Anna University | `hostel_fee_total`, `mess_fee_total` | [Anna Univ Hostel Office](https://www.annauniv.edu/hostel/) | CEG hostel annual charges. |
| `route_id_nid` | NID Ahmedabad | `mess_fee_total` | [NID Admissions](https://www.nid.edu/) | Hostel room rent is verified (₹70,000/yr); verify student mess charges per semester. |
| `route_id_iiitdmj` | IIITDM Jabalpur | `hostel_fee_total`, `mess_fee_total` | [IIITDMJ Fee Structure](https://www.iiitdmj.ac.in/) | Download Hall of Residence fees (seat rent + mess advance) per semester. |
| `route_ux_nid` | NID Ahmedabad | `mess_fee_total` | [NID Admissions](https://www.nid.edu/) | Hostel room rent is verified; verify semester mess dues. |
| `route_law_glc` | GLC Mumbai | `hostel_fee_total`, `mess_fee_total` | [GLC Mumbai Hostels](https://www.glcmumbai.com/) | Locate Government Law College hostel allocation circular and mess charges. |
| `route_econ_dse` | DSE (Delhi University) | `hostel_fee_total`, `mess_fee_total` | [Delhi University Hostels](http://www.du.ac.in/) | Check DU Post-Graduate Men's/Women's Hostel and DSE hostel fees. |
| `route_hist_jnu` | JNU New Delhi | `mess_fee_total` | [JNU Inter-Hall Administration](https://www.jnu.ac.in/iha) | Hostel rent is verified (₹240); check monthly mess billing / mess security advance. |
| `route_ds_isi` | ISI Kolkata | `hostel_fee_total`, `mess_fee_total` | [ISI Kolkata Dean Office](https://www.isical.ac.in/) | Tuition is ₹0; check student hostel room charges and mess dues. |
| `route_jour_iimc` | IIMC New Delhi | `mess_fee_total` | [IIMC New Delhi Prospectus](https://iimc.gov.in/) | Hostel rent is verified (₹40,000); check dining hall cooperative mess charges. |

---

## 3. Data Entry Formatting Checklist

When updating `data_pipeline/processed/route_costs.csv` or `salary_bands.csv`:
- [ ] Record exact `source_url` pointing directly to the official government, university, or exam authority page.
- [ ] Record `source_document` and `source_page` (e.g. `"Table 2.1, Page 14"`).
- [ ] Record `retrieved_on` in ISO format (`YYYY-MM-DD`).
- [ ] Never extrapolate from informal coaching websites, blog posts, or discussion forums.
