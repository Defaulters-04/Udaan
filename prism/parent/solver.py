"""Financial constraint solver functions for PRISM Parent Machine."""

from typing import Tuple, List, Optional
from .config import ParentSolverConfig, DEFAULT_CONFIG


def calculate_net_cost(
    tuition: float,
    living: float,
    exam_equipment: float = 0.0,
    grant: float = 0.0,
    E_exam: Optional[float] = None,
) -> float:
    """N_r = max(0, T + L + E_exam - G)."""
    e_val = exam_equipment if E_exam is None else E_exam
    return max(0.0, float(tuition) + float(living) + float(e_val) - float(grant))


def calculate_cash_available(
    savings: float, surplus: float, duration_years: float, config: ParentSolverConfig = DEFAULT_CONFIG
) -> float:
    """A_cash = 0.50*S + 12*Y*0.25*M."""
    return (config.savings_share * float(savings)) + (
        12.0 * float(duration_years) * config.surplus_share * float(surplus)
    )


def calculate_loan_needed(net_cost: float, cash_available: float) -> float:
    """L_need = max(0, N_r - A_cash)."""
    return max(0.0, float(net_cost) - float(cash_available))


def calculate_emi(loan_needed: float, config: ParentSolverConfig = DEFAULT_CONFIG) -> float:
    """EMI = L_need * i(1+i)^n / ((1+i)^n - 1), i = annual_rate/12, n = months; EMI = 0 if L_need = 0."""
    p = float(loan_needed)
    if p <= 0.0:
        return 0.0

    n = config.loan_term_months
    if n <= 0:
        return p

    annual_rate = config.annual_loan_rate
    if annual_rate <= 0.0:
        return p / float(n)

    i = annual_rate / 12.0
    factor = (1.0 + i) ** n
    return p * (i * factor) / (factor - 1.0)


def calculate_repayment_burden(
    existing_emis: float,
    emi: float,
    household_income: float,
    E_exist: Optional[float] = None,
) -> Tuple[float, Optional[str]]:
    """RB = (E_exist + EMI) / M_inc."""
    e_val = existing_emis if E_exist is None else E_exist
    e_total = float(e_val) + float(emi)
    m_inc = float(household_income)

    if m_inc <= 0.0:
        if e_total <= 0.0:
            return 0.0, "household_income M_inc <= 0; RB set to 0.0 as obligations are zero"
        return 1.0, "household_income M_inc <= 0 with active obligations; RB capped at 1.0"

    return e_total / m_inc, None


def calculate_debt_service_ratio(emi: float, starting_salary: float) -> Tuple[float, Optional[str]]:
    """DSR = 12*EMI / Y1."""
    annual_emi = 12.0 * float(emi)
    y1 = float(starting_salary)

    if y1 <= 0.0:
        if annual_emi <= 0.0:
            return 0.0, "starting_salary Y1 <= 0; DSR set to 0.0 as EMI is zero"
        return 1.0, "starting_salary Y1 <= 0 with active loan; DSR capped at 1.0"

    return annual_emi / y1, None


def calculate_family_affordability(cash_available: float, loan_max: float) -> float:
    """A_family = A_cash + L_max."""
    return float(cash_available) + float(loan_max)


def check_financial_gate(
    loan_needed: float,
    loan_max: float,
    rb: float,
    dsr: float,
    config: ParentSolverConfig = DEFAULT_CONFIG,
) -> Tuple[int, List[str]]:
    """G_fin = 1 if L_need <= L_max AND RB <= 0.50 AND DSR <= 0.20 else 0."""
    l_need = float(loan_needed)
    l_max = float(loan_max)
    rb_val = float(rb)
    dsr_val = float(dsr)

    reasons: List[str] = []

    if l_need > l_max:
        diff = l_need - l_max
        reasons.append(
            f"Loan needed (INR {l_need:,.0f}) exceeds loan limit (INR {l_max:,.0f}) by INR {diff:,.0f}"
        )

    if rb_val > config.rb_gate_max:
        diff = rb_val - config.rb_gate_max
        reasons.append(
            f"Repayment burden ({rb_val:.1%}) exceeds maximum gate ({config.rb_gate_max:.1%}) by {diff:.1%}"
        )

    if dsr_val > config.dsr_gate_max:
        diff = dsr_val - config.dsr_gate_max
        reasons.append(
            f"Debt service ratio ({dsr_val:.1%}) exceeds maximum gate ({config.dsr_gate_max:.1%}) by {diff:.1%}"
        )

    g_fin = 1 if len(reasons) == 0 else 0
    return g_fin, reasons


def calculate_grant_shortfall(
    net_cost: float,
    cash_available: float,
    household_income: float,
    existing_emis: float,
    starting_salary: float,
    loan_max: float,
    config: ParentSolverConfig = DEFAULT_CONFIG,
) -> float:
    """Shortfall = max(0, N_r - A_cash - allowable_loan) required to clear G_fin."""
    n = config.loan_term_months
    annual_rate = config.annual_loan_rate

    if n <= 0:
        emi_factor = 1.0
    elif annual_rate <= 0.0:
        emi_factor = 1.0 / float(n)
    else:
        i = annual_rate / 12.0
        factor = (1.0 + i) ** n
        emi_factor = (i * factor) / (factor - 1.0)

    # Constraint 1: L <= L_max
    cap_l_max = max(0.0, float(loan_max))

    # Constraint 2: (E_exist + EMI) / M_inc <= rb_gate_max -> EMI <= rb_gate_max * M_inc - E_exist
    if household_income > 0.0:
        max_emi_rb = max(0.0, (config.rb_gate_max * float(household_income)) - float(existing_emis))
        cap_rb = max_emi_rb / emi_factor if emi_factor > 0 else 0.0
    else:
        cap_rb = 0.0

    # Constraint 3: 12 * EMI / Y1 <= dsr_gate_max -> EMI <= (dsr_gate_max * Y1) / 12
    if starting_salary > 0.0:
        max_emi_dsr = max(0.0, (config.dsr_gate_max * float(starting_salary)) / 12.0)
        cap_dsr = max_emi_dsr / emi_factor if emi_factor > 0 else 0.0
    else:
        cap_dsr = 0.0

    allowable_loan = max(0.0, min(cap_l_max, cap_rb, cap_dsr))
    shortfall = max(0.0, float(net_cost) - (float(cash_available) + allowable_loan))
    return shortfall
