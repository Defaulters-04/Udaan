"""FastAPI thin wrapper for the PRISM Market Machine engine."""

from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import MarketSolverConfig, DEFAULT_CONFIG
from .models import (
    CareerMarketRecord,
    MarketCatalogueResult,
    CareerScoreInput,
    HandoffResult,
    SensitivityResponse,
)
from .data_loader import load_careers_snapshot, load_regional_totals_snapshot
from .scores import evaluate_market_catalogue
from .handoff import rank_careers
from .sensitivity import run_market_sensitivity


app = FastAPI(
    title="PRISM Engine - Market Machine API",
    description="Family-independent job market viability scoring, time-series forecasting, and confidence audits.",
    version="1.0.0",
)


class MarketEvaluateRequest(BaseModel):
    """Payload for POST /market/evaluate."""

    student_region: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    careers: Optional[List[CareerMarketRecord]] = None


class MarketSensitivityRequest(BaseModel):
    """Payload for POST /market/sensitivity."""

    n: int = 1000
    seed: int = 0
    student_region: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    careers: Optional[List[CareerMarketRecord]] = None


class HandoffRankRequest(BaseModel):
    """Payload for POST /handoff/rank."""

    careers: List[CareerScoreInput]
    config: Optional[Dict[str, Any]] = None


@app.get("/market/config", response_model=Dict[str, Any])
def get_market_config() -> Dict[str, Any]:
    """Retrieve default configuration parameters for the Market Machine solver."""
    return DEFAULT_CONFIG.to_dict()


@app.post("/market/evaluate", response_model=MarketCatalogueResult)
def evaluate_market_endpoint(payload: MarketEvaluateRequest) -> MarketCatalogueResult:
    """Evaluate market scores for candidate careers from snapshots or inline records."""
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        careers = payload.careers if payload.careers is not None else load_careers_snapshot()
        try:
            regional_totals = load_regional_totals_snapshot()
        except Exception:
            regional_totals = None

        return evaluate_market_catalogue(
            careers=careers,
            regional_totals=regional_totals,
            student_region=payload.student_region,
            config=config,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Market evaluation failed: {str(exc)}") from exc


@app.post("/market/sensitivity", response_model=SensitivityResponse)
def evaluate_sensitivity_endpoint(payload: MarketSensitivityRequest) -> SensitivityResponse:
    """Run Monte Carlo weight perturbation sensitivity analysis."""
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        careers = payload.careers if payload.careers is not None else load_careers_snapshot()
        try:
            regional_totals = load_regional_totals_snapshot()
        except Exception:
            regional_totals = None

        return run_market_sensitivity(
            careers=careers,
            config=config,
            n=payload.n,
            seed=payload.seed,
            regional_totals=regional_totals,
            student_region=payload.student_region,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Sensitivity analysis failed: {str(exc)}") from exc


@app.post("/handoff/rank", response_model=HandoffResult)
def rank_handoff_endpoint(payload: HandoffRankRequest) -> HandoffResult:
    """Perform multi-machine composite ranking and gating."""
    try:
        config = (
            DEFAULT_CONFIG.with_overrides(**payload.config)
            if payload.config
            else DEFAULT_CONFIG
        )
        return rank_careers(payload.careers, config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Handoff ranking failed: {str(exc)}") from exc


@app.get("/market/health")
def health_check() -> Dict[str, str]:
    """Service health check endpoint."""
    return {"status": "ok", "service": "prism-market-machine"}
