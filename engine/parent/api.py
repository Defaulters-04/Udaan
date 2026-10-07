"""FastAPI thin wrapper for the PRISM Parent Machine module."""

from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from .config import ParentSolverConfig, DEFAULT_CONFIG
from .models import (
    ParentEvaluationRequest,
    ParentEvaluationResponse,
)
from .scores import evaluate_parent_portfolio

app = FastAPI(
    title="PRISM Engine - Parent Machine API",
    description="Financial constraint solver, affordability verification, and parental family fit scoring.",
    version="1.0.0",
)


@app.get("/parent/config", response_model=Dict[str, Any])
def get_parent_config() -> Dict[str, Any]:
    """Retrieve default configuration parameters for the Parent Machine solver."""
    return DEFAULT_CONFIG.to_dict()


@app.post("/parent/evaluate", response_model=ParentEvaluationResponse)
def evaluate_parent_routes(payload: ParentEvaluationRequest) -> ParentEvaluationResponse:
    """Evaluate financial viability and family scores for candidate routes given a parent profile.

    Returns:
    - career_results: Best route and sorted alternatives per target career.
    - reports: Detailed viability and sub-score reports for every route.
    - blocked_list: Routes failing financial gates with diagnostic reasons and constructive suggestions.
    """
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        return evaluate_parent_portfolio(payload.profile, payload.routes, config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Evaluation failed: {str(exc)}") from exc


@app.get("/parent/health")
def health_check() -> Dict[str, str]:
    """Service health check endpoint."""
    return {"status": "ok", "service": "prism-parent-machine"}
