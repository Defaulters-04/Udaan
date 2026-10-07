# Udaan Backend

FastAPI backend service for Udaan.

> **Note on Question Bank**: Hardcoded stand-in for the ML question generator.

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
