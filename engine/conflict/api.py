"""FastAPI thin wrapper for the PRISM Conflict Index module."""

from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import ConflictConfig, DEFAULT_CONFIG
from .models import (
    OverallConflictReport,
    CareerConflictReport,
    ConflictEvaluation,
    StudentConflictInput,
    ParentConflictInput,
    RouteConflictInput,
    ConflictEvaluationRequest,
    NegotiationRequest,
    NegotiationResponse,
)
from .scores import (
    compute_overall_conflict,
    compute_career_conflict,
    evaluate_conflict,
    evaluate_negotiation_slider,
)

app = FastAPI(
    title="PRISM Engine - Conflict Index API",
    description="Parent-student alignment diagnosis, per-career conflict evaluation, and compromise zone solver.",
    version="1.0.0",
)


class OverallConflictRequest(BaseModel):
    """Payload for POST /conflict/overall."""

    student: StudentConflictInput
    parent: ParentConflictInput
    config: Optional[Dict[str, Any]] = None


class CareerConflictRequest(BaseModel):
    """Payload for POST /conflict/career."""

    student: StudentConflictInput
    parent: ParentConflictInput
    route: RouteConflictInput
    config: Optional[Dict[str, Any]] = None


@app.get("/conflict/config", response_model=Dict[str, Any])
def get_conflict_config() -> Dict[str, Any]:
    """Retrieve default configuration parameters for the Conflict Index module."""
    return DEFAULT_CONFIG.to_dict()


@app.post("/conflict/overall", response_model=OverallConflictReport)
def evaluate_overall_endpoint(payload: OverallConflictRequest) -> OverallConflictReport:
    """Compute family-wide overall conflict diagnosis across shared dimensions."""
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        return compute_overall_conflict(payload.student, payload.parent, config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Overall conflict evaluation failed: {str(exc)}") from exc


@app.post("/conflict/career", response_model=CareerConflictReport)
def evaluate_career_conflict_endpoint(payload: CareerConflictRequest) -> CareerConflictReport:
    """Compute per-career conflict for a specific career route."""
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        return compute_career_conflict(payload.student, payload.parent, payload.route, config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Career conflict evaluation failed: {str(exc)}") from exc


@app.post("/conflict/evaluate", response_model=ConflictEvaluation)
def evaluate_portfolio_conflict_endpoint(payload: ConflictEvaluationRequest) -> ConflictEvaluation:
    """Evaluate family conflict overall and across a list of candidate career routes."""
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        return evaluate_conflict(payload.student, payload.parent, payload.routes, config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Portfolio conflict evaluation failed: {str(exc)}") from exc


@app.post("/conflict/negotiate", response_model=NegotiationResponse)
def evaluate_negotiation_endpoint(payload: NegotiationRequest) -> NegotiationResponse:
    """Run Negotiation Explorer slider to find compromise zone careers."""
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        return evaluate_negotiation_slider(
            student=payload.student,
            parent=payload.parent,
            careers=payload.careers,
            alpha=payload.alpha,
            min_student_fit=payload.min_student_fit,
            min_family_viability=payload.min_family_viability,
            config=config,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Negotiation evaluation failed: {str(exc)}") from exc


@app.get("/conflict/health")
def health_check() -> Dict[str, str]:
    """Service health check endpoint."""
    return {"status": "ok", "service": "prism-conflict-engine"}
