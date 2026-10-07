"""
demo.py
UDAAN PRISM Engine — Student Fit Demonstrator

================================================================================
ILLUSTRATIVE DATA ONLY — ALL PROFILES AND CAREERS ARE SYNTHETIC DEMONSTRATION
BENCHMARKS CONSTRUCTED SOLELY TO VALIDATE THE ALGORITHMIC BEHAVIOR OF
THE STUDENT FIT MODULE. NO REAL-WORLD OCCUPATIONAL FORECASTS ARE REPRESENTED.
================================================================================

Runs student fit scoring on:
- 3 ILLUSTRATIVE Careers (Software Developer, Data Analyst, Clinical Doctor)
- 2 Illustrative Students (one School, one College)
"""

import json
from .models import AcademicProfile, AcademicRequirement, Career, Student
from .scoring import rank_careers


def build_illustrative_careers() -> list[Career]:
    """Returns 3 illustrative careers for demonstration purposes."""
    careers = [
        Career(
            career_id="illustrative_software_developer",
            career_name="Software Developer (ILLUSTRATIVE)",
            I_c={"R": 0.35, "I": 0.85, "A": 0.30, "S": 0.20, "E": 0.30, "C": 0.70},
            c_j={"logical": 0.80, "numerical": 0.70, "verbal": 0.50, "spatial": 0.40},
            u_j={"logical": 0.90, "numerical": 0.80, "verbal": 0.50, "spatial": 0.30},
            R_k={"python": 0.70, "algorithms": 0.60},
            s_k={"python": 0.90, "algorithms": 0.80},
            Pc_j={"openness": 0.70, "conscientiousness": 0.80},
            v_j={"openness": 0.60, "conscientiousness": 0.80},
            academic_requirements=AcademicRequirement(
                min_marks=60.0,
                required_subjects=["mathematics", "physics"],
                required_exams=[],
            ),
        ),
        Career(
            career_id="illustrative_data_analyst",
            career_name="Data Analyst (ILLUSTRATIVE)",
            I_c={"R": 0.20, "I": 0.75, "A": 0.25, "S": 0.30, "E": 0.50, "C": 0.80},
            c_j={"logical": 0.70, "numerical": 0.80, "verbal": 0.60, "spatial": 0.30},
            u_j={"logical": 0.80, "numerical": 0.90, "verbal": 0.50, "spatial": 0.20},
            R_k={"sql": 0.70, "statistics": 0.60},
            s_k={"sql": 0.90, "statistics": 0.80},
            Pc_j={"conscientiousness": 0.85, "agreeableness": 0.60},
            v_j={"conscientiousness": 0.80, "agreeableness": 0.50},
            academic_requirements=AcademicRequirement(
                min_marks=55.0,
                required_subjects=["mathematics"],
                required_exams=[],
            ),
        ),
        Career(
            career_id="illustrative_clinical_doctor",
            career_name="Clinical Doctor (ILLUSTRATIVE)",
            I_c={"R": 0.30, "I": 0.80, "A": 0.20, "S": 0.85, "E": 0.40, "C": 0.50},
            c_j={"logical": 0.70, "numerical": 0.50, "verbal": 0.75, "spatial": 0.60},
            u_j={"logical": 0.80, "numerical": 0.50, "verbal": 0.80, "spatial": 0.60},
            R_k={"clinical_diagnosis": 0.75, "patient_care": 0.80},
            s_k={"clinical_diagnosis": 0.90, "patient_care": 0.85},
            Pc_j={"agreeableness": 0.85, "conscientiousness": 0.90},
            v_j={"agreeableness": 0.85, "conscientiousness": 0.90},
            academic_requirements=AcademicRequirement(
                min_marks=60.0,
                required_subjects=["physics", "chemistry", "biology"],
                required_exams=["neet"],
            ),
        ),
    ]
    return careers


def build_illustrative_students() -> list[Student]:
    """Returns 2 illustrative students (one school, one college)."""
    students = [
        # Student 1: School Student (evaluates interest, aptitude, personality; skips skills)
        Student(
            student_id="student_arav_school",
            stage="school",
            I_s={"R": 0.40, "I": 0.80, "A": 0.35, "S": 0.30, "E": 0.45, "C": 0.65},
            a_j={"logical": 0.85, "numerical": 0.75, "verbal": 0.55, "spatial": 0.50},
            P_k={},  # Skills omitted at school stage
            P_j={"openness": 0.75, "conscientiousness": 0.70},
            risk_appetite=0.35,  # risk-averse
            domain_preference={
                "Technology & Engineering": 5,
                "Healthcare & Medicine": 3,
                "Business & Finance": 2,
                "Design & Creative": 1,
                "HSS": 2,
            },
            relocation_willingness=0.30,  # prefers staying local
            max_years_to_income=4.0,
            academics=AcademicProfile(
                marks=82.0,
                subjects={"mathematics", "physics", "chemistry", "computer science"},
                exams=set(),
            ),
        ),
        # Student 2: College Student (evaluates skills; lacks biology/NEET for medicine)
        Student(
            student_id="student_priya_college",
            stage="college",
            I_s={"R": 0.25, "I": 0.80, "A": 0.20, "S": 0.35, "E": 0.50, "C": 0.75},
            a_j={"logical": 0.80, "numerical": 0.85, "verbal": 0.65, "spatial": 0.40},
            P_k={"python": 0.85, "algorithms": 0.75, "sql": 0.80, "statistics": 0.70},
            P_j={"conscientiousness": 0.85, "openness": 0.70, "agreeableness": 0.65},
            risk_appetite=0.70,  # risk-seeking
            domain_preference={
                "Technology & Engineering": 5,
                "Healthcare & Medicine": 2,
                "Business & Finance": 4,
                "Design & Creative": 3,
                "HSS": 1,
            },
            relocation_willingness=0.80,  # willing to relocate
            max_years_to_income=3.0,
            academics=AcademicProfile(
                marks=74.0,
                subjects={"mathematics", "statistics", "computer science"},
                exams=set(),
            ),
        ),
    ]
    return students


def run_demo() -> None:
    """Executes the demonstration and prints structured outputs."""
    print("=" * 80)
    print("UDAAN PRISM ENGINE — STUDENT FIT SCORING DEMONSTRATION")
    print("Pure-Math Deterministic Recommendation & Academic Gating")
    print("=" * 80)

    careers = build_illustrative_careers()
    students = build_illustrative_students()

    for student in students:
        print(f"\nEvaluating Student: {student.student_id} (Stage: {student.stage.upper()})")
        print(f"Academics: Marks = {student.academics.marks}%, Subjects = {sorted(student.academics.subjects)}")

        ranking = rank_careers(student, careers)
        eligible, blocked = ranking.eligible, ranking.blocked

        print(f"\n--- ELIGIBLE CAREERS ({len(eligible)} found) ---")
        for idx, res in enumerate(eligible, start=1):
            print(f"  {idx}. {res.career_name} (ID: {res.career_id})")
            print(f"     * Composite Fit F_student : {res.F_student:.2f} / 100")
            print(f"     * Sub-Scores: Interest={res.InterestFit:.1f}, Aptitude={res.AptitudeFit:.1f}, "
                  f"Skill={res.SkillFit:.1f}, Personality={res.PersonalityFit:.1f}")
            print(f"     * Stage Weights: {res.weights_used}")

            if res.strengths:
                str_names = [f"{s['trait']} (+{s['surplus']:.2f}, u={s['importance']})" for s in res.strengths]
                print(f"     * Strengths (a_j >= c_j): {', '.join(str_names)}")
            else:
                print(f"     * Strengths: None")

            if res.weaknesses:
                wk_names = [f"{w['trait']} (shortfall -{w['shortfall']:.2f}, weighted -{w['weighted_shortfall']:.2f})" for w in res.weaknesses]
                print(f"     * Weaknesses (Top Deficits): {', '.join(wk_names)}")
            else:
                print(f"     * Weaknesses: None (All aptitude requirements met)")

        print(f"\n--- BLOCKED CAREERS ({len(blocked)} found) ---")
        if not blocked:
            print("  (None — Student meets academic criteria for all illustrative careers)")
        for idx, res in enumerate(blocked, start=1):
            print(f"  {idx}. {res.career_name} (ID: {res.career_id})")
            print(f"     * Composite Fit F_student : {res.F_student:.2f} (Blocked by G_acad = 0)")
            print(f"     * Potential Sub-Scores: Interest={res.InterestFit:.1f}, Aptitude={res.AptitudeFit:.1f}")
            print("     * Reasons for Ineligibility:")
            for reason in res.blocked_reasons:
                print(f"       - {reason}")

    print("\n" + "=" * 80)
    print("JSON OUTPUT VERIFICATION (Sample Result serialization):")
    sample_json = json.dumps(eligible[0].to_dict(), indent=2)
    print(sample_json[:400] + "\n  ...\n}")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
