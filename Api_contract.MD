# Udaan API contract

Single source of truth for frontend and backend. Change it before changing code, and tell the other person.

## Conventions
- Base URL (dev): http://localhost:8000
- JSON only. Field names are snake_case on the wire, and the frontend uses the same names.
- Enums: role = "student" | "parent"; lang = "en" | "hi".
- Errors always look like: { "error": { "code": "string", "message": "string" } }
  Validation errors use code "validation_error".

## Endpoints

### GET /health
200: { "status": "ok", "service": "udaan-api", "version": "0.1.0" }

(Page 1 makes no API calls. Role, name and language live in the browser session.)