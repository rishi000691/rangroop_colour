# BRAIN.md — Project Context File

## Project Name
**rangroop** — AI Skin Tone Color Suggestion Tool
Repo: https://github.com/rishi000691/rangroop

## What This Project Is
A **standalone web app** — not an e-commerce site. User uploads/captures
a selfie, the app analyzes skin tone and undertone, and returns a
recommended clothing color palette with a short explanation. That's the
entire product. No catalog, no cart, no checkout, no seller accounts.

## Why This Scope (Decisions Already Made — Don't Re-litigate)
- Originally considered as part of a full e-commerce marketplace with
  3D try-on. Both were dropped:
  - 3D try-on: Google, Myntra, Meesho (via Google Cloud), and PointAI
    (deployed on Amazon/Flipkart/Myntra) already have this live or in
    active rollout as of 2026. Not winnable for a student team.
  - Full marketplace: too large a scope, not the actual differentiator,
    and directly competes with Amazon/Flipkart/Meesho/Myntra at a scale
    a solo/small student team can't match.
- Further narrowed from "e-commerce site with AI feature built in" to
  "just the AI system" — faster to ship, easier to prove it works,
  and more flexible: it can later become an API/plugin sold to small
  sellers (Shopify/Meesho shops) instead of Claude needing to build and
  maintain a storefront to compete with them.
- Packaging decision: **standalone demo web app** (upload photo → see
  results), not API-only. Reason: needs to be demoable/shareable on its
  own for portfolio, feedback collection, and pitching, without
  requiring another product to plug into yet. Can be wrapped as an API
  later once the core logic is proven.
- Rule-based AI approach (ITA formula + seasonal color theory) chosen
  over training a custom ML classifier — no public dataset exists for
  "skin tone → best clothing colors" since it's stylist judgment, not
  objective ground truth. Rule-based is faster, explainable, and
  accurate enough for this stage.

## Core User Flow (Simple, No Accounts)
1. User lands on the page — no login required
2. Uploads a selfie or captures one via webcam
3. Backend detects face → extracts skin tone → classifies undertone
4. Undertone mapped to a seasonal color palette
5. User sees: their palette (swatches), undertone explanation, and a
   few example clothing colors that suit them (illustrative — not real
   products, not a catalog)
6. Optional: "try another photo" / download or share result

## Tech Stack (Locked In)
- Frontend: React (Vite) + Tailwind CSS
- Backend: Python FastAPI
- CV: OpenCV + MediaPipe Face Mesh
- Math/clustering: scikit-learn (K-Means), NumPy
- No database required for MVP (stateless — analyze and return result,
  nothing persisted). Add storage later only if you want to save
  history or collect feedback data.
- Deployment: Render (backend) + Vercel (frontend)

## AI Pipeline Logic (Core IP — Keep This Consistent)
**Corrected during Phase 1 build — this supersedes the earlier single-ITA
version.** ITA alone only measures lightness/melanin (L* and b*), so it
cannot distinguish warm from cool undertone if two skin tones share the
same lightness. Fixed by using two separate formulas:

1. MediaPipe Face Mesh → landmarks
2. Mask cheeks + forehead only (avoid eyes/lips/hair/shadow)
3. Convert to LAB color space (lighting-robust)
4. K-Means (k=3) → dominant skin color in LAB
5. **Skin type/depth** — ITA formula: `ITA = atan((L* - 50) / b*) × (180/π)`,
   classified using standard dermatological ITA ranges (Chardon et al.,
   1991) from Very Light to Dark
6. **Undertone** — Hue Angle formula: `arctan(b*/a*)`, categorizes
   redness (a*) vs. yellowness (b*) into warm / cool / neutral / olive
7. Lookup table: undertone + skin depth → 12-season color analysis
   palette
8. Return palette + a handful of illustrative "colors that suit you"
   swatches (hex codes), not real product matches

Phase 1 output JSON should include both `skin_type` (from ITA) and
`undertone` (from Hue Angle) as separate fields — don't collapse them
into one value.

## Explicitly Out of Scope
- E-commerce (catalog, cart, checkout, sellers)
- User accounts / auth
- 3D virtual try-on
- Mobile app (web-first)
- Trained ML undertone classifier (rule-based ITA is the approach)
- Persisting user photos/data (for MVP — respect privacy, process and
  discard unless user explicitly opts into saving results)

## Project Structure

```
rangroop/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint
│   │   ├── api/
│   │   │   └── analyze.py          # single endpoint: upload -> result
│   │   ├── cv/
│   │   │   ├── skin_tone_analyzer.py  # Phase 1 deliverable: consolidated
│   │   │   │                          # script (face detect, mask, LAB,
│   │   │   │                          # K-Means, ITA + Hue Angle). Split
│   │   │   │                          # into face_mesh.py / skin_extract.py
│   │   │   │                          # / ita_classify.py etc. ONLY if it
│   │   │   │                          # gets unwieldy — not required.
│   │   │   └── palette_lookup.py   # season/palette lookup tables (Phase 2)
│   ├── tests/
│   │   └── test_color_pipeline.py  # test ITA/KMeans on sample images
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.jsx            # upload/capture screen
│   │   │   └── Results.jsx         # palette + explanation + swatches
│   │   ├── components/
│   │   │   ├── SelfieCapture.jsx
│   │   │   ├── PaletteCard.jsx
│   │   │   └── ColorSwatch.jsx
│   │   ├── api/
│   │   │   └── client.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── tailwind.config.js
│   └── package.json
│
├── BRAIN.md                        # this file
└── README.md                       # project overview + setup
```

## Build Order (Don't Skip Ahead)
1. Backend CV pipeline first — test standalone on sample images
   (script, not API yet). Confirm ITA + palette output looks sane
   across different lighting/skin tones.
2. Wrap pipeline in a single FastAPI endpoint (`/analyze`)
3. Frontend: upload/capture screen → results screen
4. Test with 15–20 real people, compare AI undertone read to
   self-identification/stylist opinion
5. Collect feedback, THEN decide next phase (add persistence, wrap as
   API for sellers, revisit e-commerce/try-on, etc.) based on real
   usage — don't pre-build later phases before this one is validated

## Known Constraints / Things to Watch
- Lighting variation in selfies is the biggest accuracy risk — LAB
  space + normalization helps but won't fully solve it
- Camera quality varies a lot across Indian smartphone market — test on
  low-end devices, not just flagship phones
- Frame results as "suggested," not "definitive," in UI copy — ITA is a
  useful tool, not a perfect rule
- Handle photo privacy carefully: don't store images unless the user
  explicitly opts in, and say so clearly in the UI

## Founder Context (for AI assistant continuity)
Solo/small-team student founder, 3rd year Computer Engineering/IT
(CHARUSAT DEPSTAR), full-stack + AI/ML background, building this
alongside other projects (FRIDAY personal assistant, LegalEase team
project, Civic AI Seva portfolio project). Freelancing on
Upwork/Contra in parallel. Comfortable with FastAPI, React/Tailwind,
Git workflow. Uses Antigravity IDE.