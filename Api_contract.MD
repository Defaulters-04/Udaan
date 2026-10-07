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

## Families (Page 2: link the family)

- family_code: 6 characters, uppercase, alphabet ABCDEFGHJKMNPQRSTUVWXYZ23456789. Input is case-insensitive and spaces/hyphens are ignored.
- name: 1 to 40 characters after trimming.
- member_token: returned on create/join. Sent on later calls in the header X-Member-Token.
- Families live in memory for 120 minutes after the last status call, then are gone (404 family_not_found).
- Error codes used here: family_not_found, role_taken, family_full, invalid_token, validation_error.

### POST /families
Body: { "role": "student"|"parent", "name": string, "lang": "en"|"hi" }
201: { "family_code": string, "member_token": string, "role": string, "expires_at": ISO-8601 UTC string }

### GET /families/{family_code}/preview
No token. Used when someone opens an invite link.
200: { "family_code": string, "open_role": "student"|"parent"|null, "creator_name": string }  (open_role null = family already full)
404 family_not_found

### POST /families/{family_code}/join
Body: { "role": "student"|"parent", "name": string, "lang": "en"|"hi" }
200: { "family_code": string, "member_token": string, "role": string, "partner": { "role": string, "name": string }, "expires_at": string }
404 family_not_found | 409 role_taken (that role is already in the family) | 409 family_full (both roles filled)

### GET /families/{family_code}/status
Header: X-Member-Token
200: { "family_code": string, "linked": boolean, "you": { "role": string, "name": string }, "partner": { "role": string, "name": string } | null, "expires_at": string }
401 invalid_token | 404 family_not_found
Returns only role and name of each member, nothing else.

## Assessment (Page 3: student test). Student only.

Shared types
- LocalizedText = { "en": string, "hi": string }
- Question types and the answer value each takes:
  - single_choice: option id (string)
  - multi_choice: array of option ids
  - text: string (one line)
  - long_text: string (multi-line)
  - scale: integer from min to max (interest items use 1..5)
  - slider: integer from min to max (value items use 0..10)
- Question: { id: string, type: string, prompt: LocalizedText, required: boolean,
  options?: [{ id: string, label: LocalizedText }], min?: int, max?: int,
  min_label?: LocalizedText, max_label?: LocalizedText, max_length?: int, placeholder?: LocalizedText }
- Section: { id: "background"|"interests"|"aptitude"|"values"|"free_text", title: LocalizedText, questions: Question[] }
- Questions never include answer keys, scoring dimensions, or any hint of correctness.
- All calls need the X-Member-Token header. Only the student member may call them; a parent gets 403 wrong_role.
- Error codes used: invalid_token, family_not_found, wrong_role, validation_error, assessment_incomplete, already_submitted.

### GET /families/{family_code}/assessment/questions
200: { "version": string, "sections": Section[] }

### GET /families/{family_code}/assessment/progress
200: { "answers": { "<question_id>": value }, "submitted": boolean }
Only the caller's own answers.

### PUT /families/{family_code}/assessment/answers
Body: { "answers": { "<question_id>": value } }
Merges into stored answers (partial updates, overwrites per question id).
200: { "answered": int, "total": int }
422 validation_error: unknown question id, wrong value type, option id not in that question, number out of range.
409 already_submitted: after submit.

### POST /families/{family_code}/assessment/submit
200: { "submitted": true }  (idempotent: submitting again also returns 200)
422 assessment_incomplete: { "error": { "code": "assessment_incomplete", "message": string, "missing": string[] } }
  missing = ids of required questions with no answer. This is the only error that carries "missing".

### Change to GET /families/{family_code}/status (additive)
"you" and "partner" each gain "done": boolean = "has finished their part" (the student's assessment now, the parent's intake later). Existing fields are unchanged.