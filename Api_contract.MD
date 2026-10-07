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