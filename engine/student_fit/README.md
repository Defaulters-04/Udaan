# UDAAN PRISM Student Fit Engine
Pure-math, deterministic student-to-career recommendation and academic gating package (Python 3.10+, NumPy).
## How to Run: Tests: `pytest engine/student_fit/tests/` | Demo: `python -m engine.student_fit.demo`
## Inputs & Outputs
- Inputs: Student RIASEC (6), 4 aptitudes, skills, personality, academics, stage ('school'|'college'); Career requirements with weights. Normalized [0, 1].
- Outputs: Composite fit F_student in [0, 100], 4 sub-scores, academic gate G_acad, SWOT diagnostics, ranked eligible & blocked career lists.
## Key Assumptions
- Academic gate G_acad in {0, 1} is binary; failing any mandatory criteria sets F_student = 0 while preserving sub-scores.
- Aptitude strength requires u_j >= mean(u). School stage omits skill fit (w_S = 0.00).
