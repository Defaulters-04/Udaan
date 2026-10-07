# Udaan: project context (read this first, every task)

## What we're building
Udaan is career guidance for the whole family. A student and a parent answer separately (on separate devices). The app shows where they actually disagree, then a slider finds a career both sides can live with, with the affordability math behind it. The scoring and solver engine inside Udaan is called the PRISM Engine. Built for DataQuest 3.0, a 24-hour hackathon judged by tech experts and industry people.

## Repo and ownership
- `frontend/` and `backend/`: our work. Only edit what the current task names.
- `data/` and `scripts/`: owned by teammates. Never edit, create or delete anything there. Read from `data/` only when a task says so. If a file is missing, use a clearly marked stub, never invented data.
- Scoring math (fit, family viability, financial solver, conflict index, forecasts) is written by teammates. Never write your own formulas for these. The backend calls the engine module when a task says so.
- Do not invent API routes or response shapes. When backend pages start, the contract will be added at the repo root as `API_CONTRACT.md`. Follow it exactly.

## Stack
- Frontend: Next.js (App Router), TypeScript, Tailwind CSS, Zustand. Charts (Recharts) come later.
- Backend: FastAPI + Pydantic (later).
- Languages: English (`en`) and Hindi (`hi`) only.

## Design system
- Palette (define once as CSS variables / Tailwind theme, reuse everywhere):
  - paper `#F5F8FB` (page background)
  - cloud `#E3EEF8` (subtle surfaces)
  - sky `#7DBEF0` (highlights, selected states)
  - ocean `#2D6FB8` (primary actions, links)
  - midnight `#11284A` (text, strong elements)
- Text is midnight on paper. White text only on ocean or midnight. Keep text contrast at 4.5:1 or better.
- Fonts, loaded with `next/font/google` (latin + devanagari subsets):
  - Bricolage Grotesque: the "Udaan" wordmark and English headings.
  - Hind: body text, and all Hindi text including Hindi headings.
  - Do not use Inter, Roboto, Arial, Poppins, Space Grotesk or system-ui as a visible font.
- Look: calm, plain, friendly. Sentence case. No all-caps labels, no gradient washes, no grids of identical shadowed cards, no decorative blobs. Use motion sparingly: one deliberate moment per page, and always respect `prefers-reduced-motion`.
- The heading on every page is the wordmark "Udaan" (capital U only).

## Rules for all code
- Every user-facing string lives in one dictionary at `frontend/src/lib/i18n.ts`, with stable keys and both `en` and `hi`. No hardcoded text in components. Hindi is natural everyday Hindi, no formal or obscure words. The page switches language instantly.
- Session state lives in Zustand, persisted to `sessionStorage` only (nothing survives the tab). Use `skipHydration` and rehydrate in an effect to avoid hydration mismatches. Current shape: `{ role: "student" | "parent" | null, name: string, lang: "en" | "hi" }`. Extend it as pages need.
- The interest model (RIASEC or another) is not final. Keep it swappable: one registry in `frontend/src/config/`, selected by an environment variable. No page may hardcode RIASEC.
- Honesty: the LLM never produces numbers. Every number on screen comes from the engine or a cited source. Mark illustrative numbers as "illustrative". Never invent metrics or claims.
- The assessment is a screening tool, not a diagnosis. Financial data stays in the session and is never stored.
- Fairness: never reject a family's aspiration because of money. Show what would make it workable.
- Accessibility floor: mobile-first (works at 360px wide), full keyboard use, visible focus, real labels, `aria-live` for content that appears, reduced-motion respected.

## How to work
- One page per task. Do not build ahead or add features that were not asked for.
- Do not add a dependency without saying why.
- Before saying "done": run the build and lint, fix errors, and list which files you created or changed.

## Pages (build order)
1. Welcome: role, name, language
2. Link the family: 6-character code, student and parent on separate devices
3. Student assessment: 5-step stepper with autosave
4. Parent intake: form, then a confirmation screen where the parent edits values
5. Family Mirror: overlaid radar charts, Conflict Index gauge, per-dimension bars
6. Negotiation Explorer: Fit vs Family viability scatter, slider, ranked list, compromise zone
7. Career page: cost, payback, demand, exams, scholarships, skill gaps
8. What-if chat: optional, skipped for now
9. Family brief: one-page PDF with shortlist, costs, exams, SWOT, next steps

## Status
Page 1 (Welcome) in progress.