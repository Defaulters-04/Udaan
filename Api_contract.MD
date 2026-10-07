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
  min_label?: LocalizedText, max_label?: LocalizedText, max_length?: int, placeholder?: LocalizedText,
  max_select?: int }
- Section: { id: "background"|"interests"|"aptitude"|"values"|"preferences"|"free_text", title: LocalizedText, questions: Question[] }
- Sections run in this order: background, interests, aptitude, values, preferences, free_text.
- Total question count: 32. Version: "starter-2".
- Questions never include answer keys, scoring dimensions, or any hint of correctness.
- All calls need the X-Member-Token header. Only the student member may call them; a parent gets 403 wrong_role.
- Error codes used: invalid_token, family_not_found, wrong_role, validation_error, assessment_incomplete, already_submitted.

### Preferences Section (Specification)
The "preferences" section contains 6 questions (all required: true; English plus natural everyday Hindi on every text; all rupee amounts marked illustrative):
1. `pref_risk_1`: single_choice. Hypothetical job offer: "Imagine two starting job offers after college. Which would you choose?" / "मान लें कि कॉलेज के बाद आपके सामने नौकरी के दो विकल्प हैं। आप किसे चुनेंगे?". Options:
   - `safe`: "₹3.5 lakh a year, guaranteed (illustrative)" / "₹3.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)"
   - `gamble`: "50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)" / "50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)"
2. `pref_risk_2`: single_choice. Hypothetical job offer: "Imagine a different set of starting job offers. Which would you choose?" / "अब मान लें कि आपके सामने ये दो विकल्प हैं। आप किसे चुनेंगे?". Options:
   - `safe`: "₹4.5 lakh a year, guaranteed (illustrative)" / "₹4.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)"
   - `gamble`: "50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)" / "50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)"
3. `pref_risk_3`: single_choice. Hypothetical job offer: "Imagine a higher guaranteed offer vs the same variable opportunity. Which would you choose?" / "मान लें कि एक अधिक सुरक्षित विकल्प और वही अनिश्चित अवसर सामने है। आप क्या चुनेंगे?". Options:
   - `safe`: "₹5.5 lakh a year, guaranteed (illustrative)" / "₹5.5 लाख प्रति वर्ष, तय और सुरक्षित (अनुमानित)"
   - `gamble`: "50% chance of ₹10 lakh a year, 50% chance of ₹2 lakh a year (illustrative)" / "50% संभावना ₹10 लाख प्रति वर्ष की, 50% संभावना ₹2 लाख प्रति वर्ष की (अनुमानित)"
4. `pref_relocation`: single_choice. "How far are you comfortable moving for higher studies or work?" / "पढ़ाई या नौकरी के लिए आप कितनी दूर जाने में सहज हैं?". Options:
   - `home_city`: "Within our home city / town" / "अपने शहर / कस्बे में"
   - `same_state`: "Within our state" / "अपने राज्य में"
   - `anywhere_india`: "Anywhere in India" / "भारत में कहीं भी"
   - `abroad_ok`: "Abroad / International is fine too" / "विदेश जाने में भी कोई आपत्ति नहीं"
5. `pref_time_to_earn`: single_choice. "How soon do you expect to start earning after completing school?" / "स्कूल पूरा करने के बाद आप कब तक कमाई शुरू करने की उम्मीद करते हैं?". Options:
   - `within_4y`: "Within 3 to 4 years (e.g., direct degree or diploma)" / "3 से 4 साल के भीतर (जैसे डिग्री या डिप्लोमा के तुरंत बाद)"
   - `five_six`: "In 5 to 6 years (e.g., professional degree like B.Tech / MBBS / Masters)" / "5 से 6 साल में (जैसे बी.टेक, एमबीबीएस या मास्टर्स के बाद)"
   - `seven_plus`: "7+ years is fine (e.g., advanced research or specialization)" / "7 साल या उससे अधिक भी चलेगा (जैसे उच्च शोध या विशेषज्ञता)"
6. `pref_domain_wish`: multi_choice, max_select: 3. "Which career domains are you most interested in exploring? (Select up to 3)" / "आप किन क्षेत्रों में करियर बनाने के लिए सबसे अधिक उत्सुक हैं? (अधिकतम 3 चुनें)". Options are the 7 canonical domain ids from engine/domains.py:
   - `tech_engineering`: "Technology & Engineering" / "तकनीक और इंजीनियरिंग"
   - `business_management`: "Business & Management" / "बिजनेस और मैनेजमेंट"
   - `healthcare_medicine`: "Healthcare & Medicine" / "डॉक्टरी और स्वास्थ्य"
   - `design_creative`: "Design & Creative Arts" / "डिजाइन और कला"
   - `media_entertainment`: "Media & Content Creation" / "मीडिया और कंटेंट क्रिएशन"
   - `humanities_law`: "Humanities, Law & Social Sciences" / "कला, कानून और समाज शास्त्र"
   - `sciences`: "Sciences & Research" / "साइंस और रिसर्च"

### GET /families/{family_code}/assessment/questions
200: { "version": string, "sections": Section[] }

### GET /families/{family_code}/assessment/progress
200: { "answers": { "<question_id>": value }, "submitted": boolean }
Only the caller's own answers.

### PUT /families/{family_code}/assessment/answers
Body: { "answers": { "<question_id>": value } }
Merges into stored answers (partial updates, overwrites per question id).
200: { "answered": int, "total": int }
422 validation_error: unknown question id, wrong value type, option id not in that question, number out of range, too many ids for max_select.
409 already_submitted: after submit.

### POST /families/{family_code}/assessment/submit
200: { "submitted": true }  (idempotent: submitting again also returns 200)
422 assessment_incomplete: { "error": { "code": "assessment_incomplete", "message": string, "missing": string[] } }
  missing = ids of required questions with no answer. This is the only error that carries "missing".

### Change to GET /families/{family_code}/status (additive)
"you" and "partner" each gain "done": boolean = "has finished their part" (the student's assessment now, the parent's intake later). Existing fields are unchanged.

## Intake (Page 4: parent form). Parent only.

Same shapes as Assessment (LocalizedText, Question, answer values per type), with these differences:
- Question gains an optional field: max_select?: int (multi_choice only). More ids than max_select gives 422 validation_error.
- Section ids for intake: "money" | "risk" | "plans" | "hopes" | "perception".
- Total question count: 16. Version: "starter-2".
- All calls need X-Member-Token. Only the parent member may call them; a student gets 403 wrong_role.
- An answer that is an empty array or an empty string counts as unanswered (applies to Assessment too).
- Answers are never returned to the other member and never written to logs.
- Questions never include internal tags, scoring dimensions or hints.
- Error codes used: invalid_token, family_not_found, wrong_role, validation_error, intake_incomplete, already_submitted.

### Money Section Additions (Specification)
Under the "money" section, directly following `loan_band`:
1. `surplus_band`: single_choice, required: true. "How much money is left over each month after all expenses?" / "हर महीने सारे खर्चों के बाद परिवार के पास लगभग कितनी बचत बचती है?". Options (amounts marked illustrative):
   - `none`: "None" / "कुछ नहीं"
   - `under_5k`: "Under ₹5,000 (illustrative)" / "₹5,000 से कम (अनुमानित)"
   - `5k_15k`: "₹5,000 to ₹15,000 (illustrative)" / "₹5,000 से ₹15,000 (अनुमानित)"
   - `15k_30k`: "₹15,000 to ₹30,000 (illustrative)" / "₹15,000 से ₹30,000 (अनुमानित)"
   - `over_30k`: "Over ₹30,000 (illustrative)" / "₹30,000 से अधिक (अनुमानित)"
2. `emi_band`: single_choice, required: true. "What total loan EMIs does the family already pay each month?" / "परिवार हर महीने कुल कितनी लोन ईएमआई (EMI) भरता है?". Options (amounts marked illustrative):
   - `none`: "None" / "कोई ईएमआई नहीं"
   - `under_5k`: "Under ₹5,000 (illustrative)" / "₹5,000 से कम (अनुमानित)"
   - `5k_15k`: "₹5,000 to ₹15,000 (illustrative)" / "₹5,000 से ₹15,000 (अनुमानित)"
   - `over_15k`: "Over ₹15,000 (illustrative)" / "₹15,000 से अधिक (अनुमानित)"

### Domain Questions Taxonomy (Specification)
`domain_wish` (in "hopes", multi_choice, max_select 3) and `guess_domain` (in "perception", single_choice) use the 7 canonical domain ids from engine/domains.py:
- `tech_engineering`: "Technology & Engineering" / "तकनीक और इंजीनियरिंग"
- `business_management`: "Business & Management" / "बिजनेस और मैनेजमेंट"
- `healthcare_medicine`: "Healthcare & Medicine" / "डॉक्टरी और स्वास्थ्य"
- `design_creative`: "Design & Creative Arts" / "डिजाइन और कला"
- `media_entertainment`: "Media & Content Creation" / "मीडिया और कंटेंट क्रिएशन"
- `humanities_law`: "Humanities, Law & Social Sciences" / "कला, कानून और समाज शास्त्र"
- `sciences`: "Sciences & Research" / "साइंस और रिसर्च"
(`guess_domain` also retains option `not_sure`: "Not sure / Open to anything" / "पक्का नहीं पता / किसी भी क्षेत्र में").
The old 8 stand-in domain ids are replaced.

### GET /families/{family_code}/intake/questions
200: { "version": string, "sections": Section[] }

### GET /families/{family_code}/intake/progress
200: { "answers": { "<question_id>": value }, "submitted": boolean }
Only the caller's own answers.

### PUT /families/{family_code}/intake/answers
Body: { "answers": { "<question_id>": value } }
Merges into stored answers (partial updates, overwrites per question id).
200: { "answered": int, "total": int }
422 validation_error: unknown question id, wrong value type, option id not in that question, too many ids for max_select.
409 already_submitted: after submit.

### POST /families/{family_code}/intake/submit
200: { "submitted": true }  (idempotent)
422 intake_incomplete: { "error": { "code": "intake_incomplete", "message": string, "missing": string[] } }
  missing = ids of required questions with no answer.
  "assessment_incomplete" and "intake_incomplete" are the only errors that carry "missing".

### Status (no shape change)
For a parent, "done" in GET /families/{family_code}/status means the intake is submitted.

EDIT 1 (Assessment, Preferences Section). Replace the pref_risk_3 prompt with:
"Imagine one more pair of starting job offers. Which would you choose?" /
"एक और बार, मान लें कि आपके सामने नौकरी के ये दो विकल्प हैं। आप किसे चुनेंगे?"
(Options unchanged. The parent's risk_3 prompt gets the same fix if it has the old wording.)

EDIT 2 (Assessment, pref_time_to_earn). Replace the three option labels. The parent's
time_to_earn uses the SAME shared options. Ids unchanged. The old text put B.Tech (4 years)
in the "5 to 6 years" bucket, which is wrong.
- within_4y: "About 4 years (e.g., a regular degree, B.Tech or a diploma)" /
  "लगभग 4 साल (जैसे सामान्य डिग्री, बी.टेक या डिप्लोमा)"
- five_six: "About 5 to 6 years (e.g., MBBS, 5-year law, or a degree plus a Master's)" /
  "लगभग 5 से 6 साल (जैसे एमबीबीएस, 5 साल का लॉ, या डिग्री के बाद मास्टर्स)"
- seven_plus: "7 years or more is fine (e.g., MD/MS or a PhD)" /
  "7 साल या उससे ज़्यादा भी चलेगा (जैसे एमडी/एमएस या पीएचडी)"

EDIT 3. Wherever the contract says answers are never returned to the other member, add:
"The only exception is GET /families/{family_code}/mirror, which returns the derived values listed there."

EDIT 4. Add mirror_not_ready to the error codes list in Conventions.

NEW SECTION (append at the end):

## Mirror (Page 5: family comparison). Both roles.

- Both members must have submitted (status "done" true for both). Otherwise 409 mirror_not_ready.
- Error codes: invalid_token, family_not_found, mirror_not_ready.
- This is the one place the partner's answers show up, and only as the derived values below.
  Never raw answers, never money bands (surplus, EMI, savings, income, loans), never free text,
  never aptitude or interest results.
- Computed on request. Nothing stored. Answers never logged.

### GET /families/{family_code}/mirror
Header: X-Member-Token (student or parent). Both get the identical body.
200:
{
  "conflict_index": number,       // 0..100, 1 decimal, from the engine
  "dimensions": Dimension[]       // order: risk, domain, relocation, time
}

Dimension, common fields:
{ "id": "risk"|"domain"|"relocation"|"time",
  "gap": number,                  // 0..1, from the engine
  "weight": number,               // from the engine (0.25 each today)
  "kind": "scale"|"picks" }

kind "scale" (risk, relocation, time) adds:
  "steps": [{ "id": string, "label": LocalizedText }]   // ordered low to high
  "student_step": int, "parent_step": int               // index into steps
  - risk: 4 steps, ids risk_0..risk_3 = number of times the person chose the gamble in the three
    job-offer questions (amounts illustrative). Labels:
    risk_0 "Chose the guaranteed offer every time" / "हर बार पक्की कमाई वाला विकल्प चुना"
    risk_1 "Chose the gamble once" / "एक बार जोखिम वाला विकल्प चुना"
    risk_2 "Chose the gamble twice" / "दो बार जोखिम वाला विकल्प चुना"
    risk_3 "Chose the gamble every time" / "हर बार जोखिम वाला विकल्प चुना"
  - relocation and time: steps are the question's options (same ids, labels and order as
    pref_relocation / pref_time_to_earn).

kind "picks" (domain) adds:
  "options": [{ "id": string, "label": LocalizedText }]  // all canonical domains, engine/domains.py order
  "student_picks": string[], "parent_picks": string[]    // canonical ids, in options order
  "parent_guess": string | null    // parent's guess of the student's domain; null if "not sure" or unanswered

Example (shortened):
{ "conflict_index": 16.5,
  "dimensions": [
    { "id": "risk", "gap": 0.33, "weight": 0.25, "kind": "scale",
      "steps": [ ...4 steps... ], "student_step": 2, "parent_step": 0 },
    { "id": "domain", "gap": 0.0, "weight": 0.25, "kind": "picks",
      "options": [ ...7... ], "student_picks": ["tech_engineering"],
      "parent_picks": ["tech_engineering"], "parent_guess": "tech_engineering" },
    ...relocation, time... ] }

## Explorer (Page 6: negotiation explorer). Both roles.

- Both members must have submitted (status "done" true for both), else 409 explorer_not_ready.
- Error codes: invalid_token, family_not_found, explorer_not_ready.
- Same body for both roles. Deterministic: the same answers always give the same body, including the
  order of tied careers (ties are broken by the engine, stably, by career id).
- Derived values only. Never raw answers, money bands, family savings, surplus, EMIs, income or loan
  figures, interest/aptitude/SWOT breakdowns, route costs or EMI amounts, or the engine's explanation text.
- Every score is 0..100, one decimal, from the engine. Neither backend nor frontend computes scores,
  ranks, the frontier or compromise membership. They read and pass them on.
- Computed on request; may be cached in the in-memory family record; never logged.

### GET /families/{family_code}/explorer
Header: X-Member-Token (student or parent).
200:
{
  "slider": { "positions": int[], "default": int },   // positions ascending, 0..100 step 5 (21 values)
  "careers": Career[],                                // all careers, blocked ones included
  "frontier": string[],                               // Pareto frontier ids (non-blocked), ordered by viability ascending
  "compromise": { "min_fit": number, "min_viability": number } | null   // thresholds from the engine config
}

Slider meaning: position 0 = decide only by what the student would love, 100 = decide only by what the
family can afford. (The backend sends the engine alpha = 1 - position/100.)

Career:
{
  "id": string,
  "name": LocalizedText,
  "domain": string,
  "fit": number | null,                // blocked careers keep their fit
  "viability": number | null,          // null whenever the money gate blocks (the engine's 0 is a gate artifact)
  "market": number | null,             // null unless real market data exists. The engine's neutral 50.0 default is never sent
  "years_to_income": number | null,
  "conflict": number,
  "in_compromise": boolean,
  "blend": BlendPoint[] | null,
  "blocked": null | {
    "gates": ("money"|"academic")[],
    "cause": "no_route_data" | "cost" | "academic" | "other",
    "remedies": Remedy[]
  },
  "data_gaps": string[]
}

Rules
- Blocked careers are always present, never dropped or ranked: blend null, in_compromise false, not in the frontier.
- cause "no_route_data" = the data has no educational pathway for this career, so affordability cannot be
  judged. It must never be described as unaffordable, and its remedies are always []. "cost" = pathways exist
  but exceed the family's capacity. "academic" = academic gate.
- The blend score, the shown fit, viability and conflict must all come from the SAME route (the engine's best
  route for that career), so the numbers reconcile when a user looks at them side by side.
- Ties are ordered by blend score descending, then id ascending, so rank is stable.
- With no viable careers: careers all blocked, frontier [], compromise null. That is valid, not an error.
- frontier may have 0, 1 or more ids. compromise thresholds come from the engine config (x100).
- Counting careers by category (verified, blocked by cause) is allowed on the frontend. Computing scores, ranks
  or blends is not.
- Remedy.text.hi null => the frontend shows English with an "English only" note.
- null means "not supplied": hide it, never default it.