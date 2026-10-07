# Udaan Backend

FastAPI backend service for Udaan.

> **Note on Question Banks**:
> - Student Assessment Question Bank: Hardcoded stand-in for the ML question generator (Version: `starter-2`, 32 questions).
> - Parent Intake Question Bank: 16 questions (Version: `starter-2`).
> - **Illustrative Amounts**: All financial bands in the parent intake (`income_band`, `savings_band`, `loan_band`, `surplus_band`, `emi_band`) and hypothetical salaries in risk questions (`pref_risk_1..3`, `risk_1..3`) are strictly illustrative approximations.

## Dependencies & Rationale

Dependencies required by the backend service and the integrated PRISM engine:
- `fastapi` (>=0.115.0): High-performance asynchronous API framework for REST endpoints.
- `uvicorn[standard]` (>=0.30.0): Production ASGI web server.
- `pydantic` (>=2.9.0): Data parsing and model validation across schemas and engine models.
- `pydantic-settings` (>=2.0.0): Environment variable configuration management.
- `httpx` (>=0.28.0): HTTP client for FastAPI test suite.
- `pytest` (>=8.0.0): Automated test framework.
- `numpy` (>=2.0.0): Required by PRISM engine (`student_fit`, `market`) for RIASEC correlation, variance, covariance, and SWOT threshold calculations.
- `scipy` (>=1.15.0): Required by PRISM engine (`market.components`) for percentile rank computation using `scipy.stats.rankdata`.
- `pandas` (>=2.2.0): Required by PRISM engine (`market.scores`, `market.forecast`) for tabular data handling and monthly time series indices.
- `statsmodels` (>=0.14.0): Required by PRISM engine (`market.forecast`) for exponential smoothing time series forecasting (`ETSModel`).

## Installation

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` to configure environment variables:

```bash
cp .env.example .env
```

Available environment variables:
- `CORS_ORIGINS`: Comma-separated list of allowed origins (default: `http://localhost:3000`).
- `FAMILY_TTL_MINUTES`: Sliding session TTL in minutes (default: `120`).

## Running the Server

Run the development server on port 8000:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.
Health check endpoint: `GET http://localhost:8000/health`.

## Running Tests

Run the test suite with pytest:

```bash
pytest
```
