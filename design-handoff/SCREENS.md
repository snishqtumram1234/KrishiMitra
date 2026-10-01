# Screens

Per-screen specification, read from the 28 screenshots in [screenshots/](screenshots/). Endpoint names and field names
come from [API.md](../API.md) (the contract); where the design needs something the API does not provide, it is called out as
a **GAP**. Visual values are in [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

**Roles in the app:** *farmer* (any signed-in user) and *expert* (JWT `app_metadata.role = "expert"`). There is **no admin
role** in the backend. The metrics screen is expert-only because `/api/metrics/*` is, so "admin" in the design brief maps to expert.

**Languages:** all 28 screenshots are in **English**. The only Marathi text anywhere is the toggle label **मराठी**.
Every Marathi string below is therefore **not shown** and must be written and reviewed by a Marathi speaker.

| # | Screen | Role | Viewport shown | Screenshots |
|---|---|---|---|---|
| 01 | Landing | public | none | **0 (missing)** |
| 02 | Auth (sign in / create account) | public | mobile 390 | 4 |
| 03 | Farmer dashboard | farmer | mobile 390 | 4 |
| 04 | New crop check | farmer | mobile 390 | 4 |
| 05 | Analysis progress | farmer | mobile 390 | 4 |
| 06 | Result | farmer | mobile 390 | 4 |
| 07 | Expert dashboard (review queue) | expert | desktop 1440 | 4 |
| 08 | Metrics dashboard | expert | desktop 1440 | 4 |

Each folder has the four states the designer exported: **default, empty, error, loading**. Nothing else (no mobile or
desktop variants of the same screen, no Marathi, no hover or focus states).

---

## 01 · Landing

**No screenshots were provided**, so there is nothing to document. The auth screen has a hero headline ("Check your
soybean crop from a photo.") and a "Sign in to see your crop checks…" line, which may be intended to double as the
landing page. **Decision needed:** is there a separate marketing landing page, or does `/` redirect to sign-in? The
folder [screenshots/01-landing/](screenshots/01-landing/) is empty (holds only `.gitkeep`).

---

## 02 · Auth

**Purpose:** sign in or create an account. **Role:** public (everyone starts here). **Files:** `screenshots/02-auth/`

| File | State |
|---|---|
| `auth-sign-in-default-en.png` | Sign-in tab, filled form |
| `auth-create-account-empty-en.png` | Create-account tab, empty form (exported as "Empty (new account)") |
| `auth-sign-in-error-wrong-password-en.png` | Wrong email or password |
| `auth-sign-in-loading-en.png` | Submitting ("Signing in…") |

**Layout, top to bottom**
1. Header row: leaf logo + "KrishiMitra" (left), **English | मराठी** toggle (right).
2. Hero headline "Check your soybean crop from a photo." and, in sign-in, the subtext "Sign in to see your crop checks and any
   answers from an agriculture expert." (Create-account swaps these for the headline "Create your account" and "One account
   keeps all your crop checks and expert answers together.")
3. Segmented tabs **Sign in | Create account**.
4. Sign-in form: **Email**, **Password** with a right-aligned link **Forgot password?**, primary button **Sign in**.
   Create form: **Email** (placeholder "you@example.com"), **Password** (placeholder "At least 6 characters"), primary button
   **Create account**, and the note "We'll email you a link to confirm your address before your first check."
5. Footer line: "Answers are preliminary guidance, never a confirmed diagnosis." (the error state shows instead: "Signed out because
   your session expired? Sign in again to continue where you left off.")

**States**
* Error: a pink banner "Email or password is wrong" with "Check both and try again. Passwords are case-sensitive.", the
  password field gets a red border, and the text "This password doesn't match the account." appears under it. (The
  subtitle is dropped in this state.)
* Loading: both inputs go `sunken` and disabled, the button turns lighter green with a spinner and "Signing in…".

**API:** none of the backend `/api` routes. Auth is done **in the browser against Supabase Auth**
(`signInWithPassword`, `signUp`, `resetPasswordForEmail`), which returns the `access_token` that every later call sends
as `Authorization: Bearer`. After sign-in, read `app_metadata.role` from the token to send experts to the review queue and
farmers to the dashboard.

**MISSING**
* **Forgot-password flow** (the link exists, no screen): request, "check your email", reset form, expired link.
* **After sign-up:** the "confirm your email" waiting screen and the "email not confirmed" sign-in error.
* **Create-account errors:** email already registered, weak password, invalid email, network error.
* **Sign-in errors beyond wrong password:** network failure, too many attempts, unconfirmed email.
* **Session-expired** as its own state (only a footer hint exists). Required, because every API call can return 401.
* **Marathi** version of any of this. The toggle changes the UI language, but no Marathi screen exists.
* Focus and validation-on-blur states, show/hide password.

---

## 03 · Farmer dashboard

**Purpose:** the farmer's home: start a new check, see current weather, and see recent checks and their status.
**Role:** farmer. **Files:** `screenshots/03-farmer-dashboard/`

| File | State |
|---|---|
| `farmer-dashboard-default-en.png` | 3 checks, live weather |
| `farmer-dashboard-empty-no-checks-en.png` | No checks yet, live weather |
| `farmer-dashboard-error-load-failed-en.png` | Checks failed to load, **and** weather shown as an old cached reading |
| `farmer-dashboard-loading-en.png` | Skeletons |

**Layout, top to bottom**
1. App bar: leaf + "KrishiMitra" (left), user icon (right).
2. Title **Your crop checks**.
3. Big green action card **New crop check** / "Leaf close-up photo + your question" (camera icon).
4. **Weather card** "PUNE WEATHER" + badge **Live**: **23°C**, "Rain next 24 h: **0.8 mm**", "Chance up to **71%**", "Humidity 92%",
   "Wind 0.8 km/h", and a monospace provenance line "Open-Meteo forecast-model data (live), for 01 Oct 02:00 IST".
5. Eyebrow **RECENT CHECKS · 3** then a card per check: title, status badge, meta line.
   * "Which pesticide and how much?" · **With an expert** · "Pune · 01 Oct, 02:01"
   * "Will it rain in my area?" · **Guidance ready** · "Pune · 01 Oct, 02:01"
   * "Yellow spots on leaves" · **Guidance ready** · "Pune · R3 · 01 Oct, 02:00"

**States**
* Empty: dashed card with a leaf icon, **No crop checks yet**, "Photograph one affected leaf up close and tell us what
  you see. You'll get a preliminary reading and a clear next step.", primary button **Start your first check**. The weather card remains.
* Error: pink card **Couldn't load your checks**, "Check your internet connection and try again. Your past checks are saved
  and will appear once you're back online.", **Try again**. The weather card shows badge **Old reading**, no rain row, the text "Live weather
  isn't responding. This reading is more than 6 hours old, so it isn't used in your crop advice.", and the provenance line
  "Open-Meteo forecast-model data (cached), for 30 Sep 17:00 IST". This matches the backend's stale-weather rule (6 hours).
* Loading: skeleton weather card, three skeleton check cards, "Loading your checks…". The "New crop check" button is already live.

**API**
| UI | Call | Fields |
|---|---|---|
| Check list | `GET /api/cases` | `symptom_context` (title), `district`, `growth_stage`, `created_at`, `decision_state` (badge) |
| Weather card | `GET /api/weather?district=<d>` | `source`, `stale`, `temperature_c`, `rain_next_24h_mm`, `rain_probability_max_pct`, `humidity_pct`, `wind_speed_kmh`, `observed_at`, `source_label` (shown as the provenance line) |
| Open a check | navigate to Result | uses `case_id` |

**GAPS and MISSING**
* **No badge designed for 4 of the 5 states.** Only "With an expert" (`EXPERT_REVIEW`) and "Guidance ready"
  (`PRELIMINARY_GUIDANCE`) exist. Needed: `NEEDS_BETTER_IMAGE`, `NEEDS_MORE_CONTEXT`, `UNSUPPORTED`, "not checked yet"
  (`decision_state` is `null`), and the expert sub-states ("Expert asked you a question" = `awaiting_farmer`, "Expert
  replied" = `reviewed`). The list API returns only `decision_state`; the expert status needs `GET .../analysis` per check
  (**GAP:** an N+1 call, or add `expert_status` to the list response).
* **Weather district:** the card says "PUNE". There is no user profile or "my district" endpoint. Use the latest case's
  district, a stored preference, or ask. (Decision needed.)
* **Weather source variants:** only `live` and stale `cached` are designed. The API also returns fresh `cached`, `demo`
  (labelled "DEMO data for testing only, not a real forecast") and `unavailable`.
* The weather card cannot show "rain next 24 h" in the stale state by design; keep that hidden when `stale` is true.
* Tapping a check card: no pressed state, no swipe or delete (no delete endpoint).
* User-icon menu (profile, sign out, language) is **not shown**.
* No language toggle on this screen. Where does a signed-in farmer switch UI language?
* "Your past checks are saved and will appear once you're back online" promises offline behaviour. Nothing in the backend
  or the design implements offline storage. Reword or build it.
* Pull-to-refresh, pagination (the API has none), and a long-list state.

---

## 04 · New crop check

**Purpose:** create a case, attach photos, and start the analysis. **Role:** farmer. **Files:** `screenshots/04-new-crop-check/`

| File | State |
|---|---|
| `new-crop-check-default-en.png` | Filled: photo ready, question typed, details filled |
| `new-crop-check-empty-en.png` | Blank form, "Check my crop" disabled |
| `new-crop-check-error-validation-en.png` | Two validation errors |
| `new-crop-check-loading-submitting-en.png` | Bottom sheet "Sending your check" over the form |

**Layout, top to bottom** (mobile, one long scroll)
1. Top bar: back arrow + **New crop check**.
2. *(Error state only)* summary banner "2 things to fix before we can check" with jump links "Close-up photo is too large" and
   "Start date is in the future".
3. **1 · Leaf close-up** [Required]. Empty: dashed box "Photograph one affected leaf up close" with **Take photo** and **From
   gallery** and the hint "JPEG, PNG or WebP, up to 10 MB". Filled: thumbnail, "leaf.jpg", "JPEG · 205 KB", pill **Ready**, **Retake**.
   Tips under it: "Daylight, no glare on the leaf", "Hold steady so the spots are sharp", "One leaf fills most of the frame".
4. **2 · Field photo** [Optional]. Dashed row "Add a photo of the field": "Helps when the close-up alone isn't clear".
5. **3 · What's happening?** Label "Describe the problem or ask a question", textarea (placeholder "e.g. Yellow spots on older
   leaves after rain"), counter "0 / 2000".
6. **4 · Crop and place.** **Crop** (locked: "Soybean"), **District** (select, "Pune"). Note "KrishiMitra covers soybean in
   Maharashtra for now."
7. **5 · Details** [Optional]. **Growth stage** (select: "Choose a stage"; filled example "R3 · beginning pod"), **Symptoms
   started** (date, shown `dd-mm-yyyy`), **Recent rain** (text; placeholder "e.g. none, light, heavy"), **Anything else you
   noticed** (text; placeholder "Which leaves, how many plants…").
8. **Answer in** English | मराठी toggle, then primary button **Check my crop**.

**States**
* Empty: submit disabled (grey). Upload box in its dashed empty form.
* Error: photo card turns red, thumbnail shows the file "IMG_2041.jpg · JPEG · 12.4 MB", pill **Not uploaded**, text "This photo
  is over 10 MB. Retake it, or choose a smaller copy from your gallery." with **Retake** and **From gallery**. The date field is
  red with "The start date can't be after today (1 Oct 2026)." The submit button stays enabled.
* Loading: a bottom sheet **Sending your check** over a darkened form: ✓ "Details saved", ⟳ "Uploading close-up photo" with a
  progress bar "140 of 205 KB", ○ "Start the crop check", and "Keep this screen open until the photo finishes uploading."

**API** (the three steps in the sheet map to three calls, in order)
1. `POST /api/cases` (JSON) → "Details saved"
2. `POST /api/cases/{id}/images` (multipart) once for `kind=leaf_closeup`, and once more for `kind=field_overview` if added → "Uploading…"
3. Go to Analysis progress, which calls `POST /api/cases/{id}/analyze` → "Start the crop check"

| Field in the design | `CaseCreate` field | Rules enforced by the API |
|---|---|---|
| What's happening? | `symptom_context` | required, 1 to 2000 chars |
| Crop (locked) | `crop` = `"soybean"` | anything else is 422 |
| District | `district` | not validated by the case API, but weather needs a known Maharashtra district |
| Growth stage | `growth_stage` | optional, max 100 chars |
| Symptoms started | `symptom_started_at` (`YYYY-MM-DD`) | cannot be in the future |
| Recent rain | `recent_rainfall` | optional, max 200 |
| Anything else you noticed | `description` | optional, max 2000 |
| Answer in | `language` = `en` or `mr` | exactly those two values |

Client checks mirror the API: image max 10 MB (413), type JPEG, PNG or WebP (415, sniffed from the bytes), date not in the future (422).

**GAPS and MISSING**
* **The photo is marked Required, which blocks 6 of the app's 7 routes.** The backend routes weather, advisory, treatment-safety,
  expert-request and general questions **without any photo**. With a mandatory photo, a farmer can never ask "Will it rain?" or
  "I want to talk to an expert". Decide: keep image-first (and drop those routes from the MVP UI), or make the photo
  optional and let the orchestrator route. The orchestrator already returns `NEEDS_BETTER_IMAGE` if no photo is sent for a
  crop-health question.
* **"Anything else you noticed" feeds the intent router** (the description is appended to the question). Stray words can change the route.
  Label it clearly, or send it separately.
* **Growth stage values:** the design shows "R3 · beginning pod". Decide the stored value (`"R3"` or the label); the result
  and expert screens display it back.
* **Upload progress:** `fetch` cannot report upload progress; use `XMLHttpRequest` (or similar) to get "140 of 205 KB". The
  field photo's upload is not represented in the 3-step sheet.
* **Missing states:** network failure during create or upload (with retry that does not create a duplicate case); server
  415 or 413; the case was created but the upload failed (orphan case); camera or gallery permission denied; photo too
  small or blurry **before upload** (the quality gate runs server-side, after upload); crop other than soybean (field is
  locked, fine); district list (36 districts: single select or searchable); unsaved-changes prompt on back; draft restore.
* The Marathi placeholders and tips; the "Answer in" toggle sets `language`, but **the backend never uses it** (see Cross-cutting issues).
* Date field shows `dd-mm-yyyy`; the API needs ISO `YYYY-MM-DD`. Convert in the client, and check Marathi locale formatting.

---

## 05 · Analysis progress

**Purpose:** show the orchestrator working, step by step, instead of a spinner. This is the visible proof of the
orchestration idea. **Role:** farmer. **Files:** `screenshots/05-analysis-progress/`

| File | State |
|---|---|
| `analysis-progress-default-mid-run-en.png` | Image route running; steps 1 and 2 done, step 3 active |
| `analysis-progress-empty-no-closeup-en.png` | Stopped at the photo check: no close-up photo |
| `analysis-progress-error-step-failed-en.png` | Vision step failed, sent to an expert |
| `analysis-progress-loading-starting-en.png` | Just started, route not yet known |

**Layout, top to bottom**
1. Title **Checking your crop** + status badge (Working / Needs photo / Sent to expert / Starting).
2. Question card: thumbnail (leaf, or a dashed empty box) + "Yellow spots on leaves" + "Pune · R3 · close-up photo" (or "no photo yet").
3. **ROUTE · image_diagnosis** eyebrow and a plain-language sentence ("A crop-health question with a photo, so we check the photo before reading it.").
4. **The step timeline** (this is the core of the screen):

| Design label | Backend step | Mono line shown | Right side |
|---|---|---|---|
| Understand the question | `intent_router` | "Crop health with a photo · 0.80", then `intent_router · keyword-intent-rules · matched "spot", "leaves"` | `0 ms` |
| Check photo quality | `quality_gate` | "Passed · score 100/100 · sharp, well lit", `quality_gate · opencv-quality-gate` | `35 ms` |
| Reading the leaf… (active) → Read the leaf | `vision` | `vision · soybean-mobilenetv3-onnx` | latency |
| Find guidance | `advisory` | `advisory · placeholder-advisory` | latency |
| Weather (dashed, conditional) | `weather` | "Only if the leaf reading is above 0.85", `weather · weather-adapter` | latency |
| Decide what to tell you | the policy decision (`decision:<STATE>` in `route_trace`) | none | none |

   Step icons: green ✓ done, spinning ring active, empty circle pending, dashed circle = conditional or skipped (title
   struck through, "Skipped · nothing to read"), amber "!" = stopped for a fixable reason, red ✕ = failed, blue ✓ = decided.
5. Footer or action card, by state:
   * Mid-run: "Most checks finish in under a second. The result is saved to Your crop checks."
   * No photo: amber card **Add a close-up photo** "We need one sharp photo of an affected leaf, taken in daylight, before we can say
     anything about it." + primary **Add close-up photo**, code line `NEEDS_BETTER_IMAGE · quality:missing_image`.
   * Failed: blue card **An expert will look at this** "We couldn't read your photo automatically, so an agriculture expert will
     review it. Their answer will appear in Your crop checks." + **Go to my checks**, code line
     `EXPERT_REVIEW · sources_unavailable:vision_error`.
   * Starting: "Photo uploaded. The steps appear once we know which route your question takes." with skeleton rows.

**Requirement check: orchestration steps, not a plain spinner**
* Quality check ✓ ("Check photo quality"). Vision model ✓ ("Read the leaf"). Weather ✓ (conditional on confidence above 0.85,
  correctly matching the backend). Advisory search ✓ ("Find guidance"). Question understanding ✓ (extra step).
* **Safety policy: only partly.** The last step is "Decide what to tell you". It never says "safety" or "policy". Since the
  safety rules are the product's differentiator, label it explicitly (for example "Apply safety rules"). Note that the policy
  decision is not a timed model call in the API (it appears only as `decision:<STATE>` in `route_trace`), so it has no latency to show.
* Not a plain spinner ✓. Even the loading state is a labelled active step plus skeleton rows.

**API**
* Start: `POST /api/cases/{id}/analyze` (synchronous; returns when finished).
* Draw the timeline from the response: `result.path` (route), `result.calls[]` (`route`, `model`, `latency_ms`, `outcome`,
  `output`), `result.route_trace`, `result.skipped_steps`, `result.intent`, `result.intent_confidence`,
  `calls[].output.matched` (matched keywords), `calls[quality_gate].output.score/issues/next_action`.
* `GET /api/runs/{routing_run_id}` returns the same trace in a flatter form (`steps[]`, `skipped_steps`).

**GAPS and MISSING**
* **"Mid-run" cannot be live with the current API.** `analyze` returns everything at once, after the work is done (typically
  tens to a few hundred ms). The design's half-finished state (steps 1 and 2 done, 3 spinning) would have to be **faked**, and the
  brief forbids mock data. Options: (a) show the real timeline only after the response, with the loading state in between
  (honest, recommended); (b) add a streaming or polling endpoint to the backend. **Decision needed.**
* **Only the `image_diagnosis` route is designed.** Missing: progress copy and steps for `weather`, `treatment_safety`,
  `advisory_lookup`, `general_crop_question`, `expert_escalation` (short, 1 to 2 steps) and `unsupported_request`.
  Without them, every non-image route has nothing to render.
* Missing states: all steps done, then the transition to Result; a slow step (weather can take up to 3 s); a step with
  `outcome: "error"` for steps other than vision; an `unreadable`, blurry, dark or small photo (`NEEDS_BETTER_IMAGE` with
  the specific tip and `next_action`, only "missing photo" is shown); `NEEDS_MORE_CONTEXT`; network failure on the
  request itself; user leaves the screen mid-request.
* "Go to my checks" and the footer say "Your crop checks": a nav label used mid-sentence with a capital. Copy nit.
* Raw model and route names (`soybean-mobilenetv3-onnx`, `intent_router`, `sources_unavailable:vision_error`) are shown to
  farmers. Good for transparency, but confirm that is wanted for farmers (vs experts only) and how to present them in Marathi.
* Weather is shown as skipped here but "ran" can't be seen anywhere; show a completed weather step with the source label.

---

## 06 · Result

**Purpose:** show what the check found, how sure it is, what is missing, where the information came from, what to do next,
and the safety note. **Role:** farmer. **Files:** `screenshots/06-result/`

| File | State |
|---|---|
| `result-medium-confidence-en.png` | Default: `PRELIMINARY_GUIDANCE`, confidence 0.65 (medium band) |
| `result-empty-not-analyzed-en.png` | Case saved but never analyzed |
| `result-error-load-failed-en.png` | Connection dropped |
| `result-loading-en.png` | Skeleton |

**Layout, top to bottom (default state)**
1. Top bar: back + **Crop check result**.
2. Badge **Preliminary guidance** + "01 Oct 2026, 02:00 IST"; line "You asked: "Yellow spots on leaves"".
3. **POSSIBLE CONDITION** card: headline **Rust-like signs**; "The photo may show signs of rust. This is a preliminary
   observation, not a confirmed diagnosis."; divider; **Confidence** "**Medium · 0.65**" over the three-segment band (Low · under 0.60 /
   Medium / High) with a marker; "At medium confidence we share general information and ask one question. No treatment is suggested."
4. **WHAT WE OBSERVED**: thumbnail, "**Photo check passed** · 100/100", "Sharp, well lit, leaf fills the frame · 640 × 480";
   rows Leaf reader = "Rust-like · 0.65", You noticed = "Spots on lower leaves", Growth stage = "R3 · beginning pod",
   Started = "25 Sep 2026 · 6 days ago", Recent rain = "Heavy rain last week".
5. **MISSING INFORMATION**: ① "Which leaves show the spots" / "Older, younger or both. Answer in Next step." (amber number);
   ② "Field photo" / "Optional. Shows how widely it has spread." (neutral number).
6. **SOURCE**: "Placeholder advisory: rust_like", "Publisher: placeholder", pills **Verified**, **Up to date**, **General text**,
   "Retrieved 01 Oct 2026, 02:00 IST".
7. **NEXT STEP** (emphasis card): "Are the symptoms on older leaves, younger leaves, or both?" with chips **Older leaves**
   (selected) / **Younger leaves** / **Both**; "Add detail (optional)" input ("Mostly the older lower leaves"); **Send answer**;
   outline **Add field photo**.
8. **Safety note** (dark): "KrishiMitra never gives pesticide names or doses. Before spraying anything, talk to your local
   Krishi Vigyan Kendra or agriculture officer."
9. **Route details** accordion (open): Question type `crop_health_image · 0.80`, Rule `keywords:crop_health_image`, Path
   `image_diagnosis`, Decision `PRELIMINARY_GUIDANCE · mid_confidence`, Total `55 ms · $0.00002`, then a row per step with
   latency and cost (`intent_router` 0 ms $0, `quality_gate` 35 ms $0, `vision` 20 ms $0.00002 with `rust_like 0.65`,
   `advisory` 0 ms $0 "1 source").

**Requirement check (the brief's seven elements): all present**

| Required | Where | Verdict |
|---|---|---|
| Observed evidence | "What we observed" | ✓ |
| Possible condition | "Possible condition: Rust-like signs" | ✓ (worded as possible, never definite) |
| Confidence band | "Confidence" band with Low / Medium / High | ✓ (only the Medium state is shown) |
| Missing information | "Missing information" | ✓ |
| Verified source with date | "Source" with Verified and "Retrieved …" | ⚠ present, but see issues below |
| Next action | "Next step" | ✓ |
| Safety note | dark "Safety note" card | ✓ |

**"Confirmed diagnosis" wording check: no violation.** Every occurrence is a negation: Result "This is a preliminary
observation, not a confirmed diagnosis"; Login footer "Answers are preliminary guidance, never a confirmed diagnosis";
Expert review hint "Still not a lab-confirmed diagnosis". No text anywhere calls a result a diagnosis, a detection or a
confirmation. Keep the negation intact in Marathi (see issues).

**States**
* Empty (404 "Case has not been analyzed yet"): badge **Not checked yet**, "Saved 01 Oct 2026, 02:00 IST", dashed card "This check hasn't run yet" "Your question and photo are saved. Run the check to
  see what the photo may show and what to do next." + **Run the check**.
* Error: pink card **Couldn't load this result** "The connection dropped before your result arrived. Your check is saved, so nothing is lost." +
  **Try again** / **My checks**, **and the dark safety note** "Until you see a result, don't spray anything based on a guess. Your local
  Krishi Vigyan Kendra can advise." (a good touch: safety shown even on failure).
* Loading: skeletons for the badge row, question line, condition card and evidence card; "Loading your result…".

**API**
| UI | Call | Fields |
|---|---|---|
| Page data | `GET /api/cases/{id}/analysis` | `state`, `result.message`, `result.reason`, `result.preliminary_label`, `result.confidence`, `result.follow_up_question`, `result.sources`, `result.calls`, `created_at`, `expert` |
| Question, stage, date, rain, "You noticed" | `GET /api/cases/{id}` | `symptom_context`, `growth_stage`, `symptom_started_at`, `recent_rainfall`, `description` |
| Photo check / Leaf reader | from `result.calls` | `quality_gate.output.score/details` (size, sharpness, brightness), `vision.output[0].label/confidence` |
| Route details | `GET /api/runs/{routing_run_id}` | `intent`, `intent_confidence`, `intent_rule`, `path`, `decision_state`, `reason`, `steps[]`, `total_latency_ms`, `total_cost_usd` |
| Send answer / Add field photo | `POST /api/cases/{id}/follow-up` (multipart `answer`, `file`, `kind=field_overview`) | returns the new analysis |
| Run the check (empty state) | `POST /api/cases/{id}/analyze` | |
| Confidence band | thresholds 0.60 and 0.85 | Low < 0.60, Medium 0.60 to 0.85 inclusive, High > 0.85 (same as the backend) |
| Safety note | static copy | |

**ISSUES and GAPS in the design (the important ones)**
1. **A placeholder is presented as "Verified" and "Up to date".** The source card reads "Placeholder advisory: rust_like /
   Publisher: placeholder" with a green **Verified** pill. That is because the backend's placeholder advisory is flagged
   `verified: true` (`advisory_service.py`). Showing "Verified" for a placeholder is exactly the kind of false assurance
   the project forbids. Fix the data (placeholder sources must be `verified: false`) and add a visible state for "no verified source".
2. **The date is when we fetched it, not the source's date.** "Retrieved 01 Oct 2026" is a retrieval time. The brief asks for
   a verified source *with date*. `AdvisorySource` has **no date field** (only `title`, `publisher`, `verified`, `stale`,
   `structured`). **GAP:** add `published_at` / `reviewed_at` and a retrieval time to the API before this card can be truthful.
3. **"Missing information" is not in the farmer's API response.** Only the expert snapshot has `missing_information`. The
   farmer view must be derived on the client (from `follow_up_question`, no `field_overview` image, empty optional case
   fields), or the API must return it. **GAP / decision.**
4. **The quick-reply chips can't come from the API.** `follow_up_question` is one English sentence. "Older leaves / Younger
   leaves / Both" must be hard-coded per `reason` (here `mid_confidence`) or the API must return `follow_up_options`. **GAP.**
5. **The design's wording differs from the backend's `message`.** Backend: "The photo may show signs of rust like." (it
   formats the label `rust_like` as "rust like"). Design: "Rust-like signs" and "signs of rust". Either fix the backend text
   or build the copy in the frontend from structured fields (`state`, `reason`, `preliminary_label`, band). The second is
   also needed for Marathi (see Cross-cutting issues).
6. **The decimal "0.65" next to "Medium" can be misread as a 65 % chance.** The model's score is not a calibrated probability.
   Consider showing only the band to farmers and keeping the decimal in "Route details".
7. **Only one outcome is designed.** Missing result variants: High confidence (with weather note), Low confidence /
   `NEEDS_MORE_CONTEXT` ("add a field photo"), `NEEDS_BETTER_IMAGE` (with the specific retake tip and `next_action`),
   `EXPERT_REVIEW` (what the farmer sees while waiting), expert **reply** states (`reviewed` with the expert's label and notes,
   `awaiting_farmer` showing the expert's question and a reply box), `UNSUPPORTED`, and the non-image routes: weather answer
   (with source label and "DEMO" or "cached" labelling), advisory or general answer, and the treatment-safety escalation message.
   The condition names for `healthy`, `leaf_spot_like`, `insect_damage` and `unknown` are also not shown (for example
   "Healthy-looking leaf", "Spot-like signs", "Insect damage signs", "We can't tell").
8. **Low and High band colours are not shown** (see DESIGN_SYSTEM.md 1.4).
9. **Route details are open and show raw codes to farmers.** Suggest collapsed by default.
10. After "Send answer": loading, success (new analysis replaces the page?), and error states are not designed. The follow-up
    re-runs the whole orchestration, so it needs the progress screen again.
11. History: a farmer who re-analyzes sees only the latest analysis (`/analysis`). No "previous results" view.
12. Share, print, or save. Not shown. (Not required.)

---

## 07 · Expert dashboard (review queue)

**Purpose:** let an agriculture expert review escalated cases and reply. **Role:** expert only. **Viewport:** desktop 1440.
**Files:** `screenshots/07-expert-dashboard/`

| File | State |
|---|---|
| `expert-dashboard-default-en.png` | Queue of 3, first case open, "Ask the farmer for more" selected |
| `expert-dashboard-empty-no-pending-en.png` | No pending cases, nothing selected |
| `expert-dashboard-error-not-expert-en.png` | 403, this account lacks the expert role |
| `expert-dashboard-loading-en.png` | Skeletons |

**Layout**
1. Top nav: leaf + KrishiMitra, tabs **Review queue** (active) / **Metrics**, **Expert** badge, **Sign out** button.
2. **Left column "Review queue":** filter chips **Pending review · 3**, **Awaiting farmer**, **Follow-up received**, **Reviewed**, **All**.
   Queue items: title, date ("01 Oct, 02:01"), reason tag + district tag:
   * "Which pesticide and how much?": **Treatment question**, Pune
   * "I want to talk to an expert": **Farmer asked for expert**, Pune
   * "Holes and dark patches on leaves": **Low photo confidence**, Latur
3. **Right panel, case detail:**
   * Eyebrow "CASE 19463E4C · ESCALATED 01 OCT 2026, 02:01 IST", status badge **Pending review**, the question as the title,
     monospace "treatment_needs_expert · run 6c763648".
   * Meta grid: District, Growth stage, Symptoms started, Recent rainfall (each "Not given" when empty), Question type
     (`treatment_safety`), Path (`treatment_safety`).
   * **Missing information** list ("A verified treatment source for this question", "Field overview photo", "Growth stage",
     "When the symptoms started", "Recent rainfall"); right column: **Photos** "No photos attached to this case.",
     **Sources** "No verified source found.", **Farmer follow-ups** "None yet."
   * **Model predictions** table: STEP, MODEL, LABEL, CONFIDENCE, OUTPUT (`intent_router`, `keyword-intent-rules`, —, 0.95,
     `guard:treatment_safety · matched "pesticide"`). "History: 1 escalation for this case (this one)."
   * **Your review:** **Decision** as 4 radio cards:
     "Likely condition" (hint: "Pick a category. Still not a lab-confirmed diagnosis."),
     "Not enough evidence" ("Nothing can be said from what was sent."),
     "Can't identify" ("You don't recognise what this is."),
     "Ask the farmer for more" ("Notes required: say what to send.", selected). **Category** select (disabled: "Only for
     'Likely condition'"). **Notes to the farmer** textarea with the counter "53 / 4000" and the amber warning "The farmer sees
     these words as written. They aren't filtered, so never include pesticide names or doses." **Recommended advisory
     (optional):** Title, Publisher, Link. Button **Send request to farmer** with "Case moves to Awaiting farmer."

**States**
* Empty: dashed card "No cases waiting for review" "New escalations appear here as soon as a farmer's check needs an expert." + **View follow-ups
  received**; right panel "Nothing selected" "Choose a case from the queue to see the farmer's question, photos and model predictions."
* Error: centred pink card **This account can't open the review queue** "The queue is only for agriculture experts. If you've just been given
  expert access, sign out and sign in again so your account picks it up." + "Still blocked? Ask an admin to confirm your
  account has the expert role." + **Sign out and sign in again** / **Try again**, code line `403 · Expert role required`.
* Loading: skeleton queue items and detail blocks, "Loading cases…".

**API**
| UI | Call | Fields |
|---|---|---|
| Queue and chips | `GET /api/expert/cases?status=pending_review` (also `awaiting_farmer`, `follow_up_received`, `reviewed`, `all`) | `case_id`, `question`, `district`, `escalation_reason`, `status`, `created_at` |
| Chip counts ("· 3") | no count endpoint | derive from `?status=all`, or one call per status. **GAP.** |
| Detail panel | `GET /api/expert/cases/{case_id}` | `current` and `history[]`: `snapshot` (question, district, growth_stage, symptom_started_at, recent_rainfall, intent, path, images, predictions, missing_information, sources, follow_ups), `escalation_reason`, `routing_run_id`, `created_at` |
| Submit | `POST /api/expert/cases/{case_id}/review` | `decision` = `likely` / `insufficient` / `unknown` / `request_more`; `label` (only with `likely`); `notes` (required with `request_more`, max 4000); `recommended_advisory` {`title`, `publisher`, `url`} |

Decision names map: Likely condition → `likely`; Not enough evidence → `insufficient`; Can't identify → `unknown`; Ask the
farmer for more → `request_more`. The reviewer id comes from the token.

**GAPS and MISSING**
* **Experts cannot see the photos.** The panel says "No photos attached to this case" but the API only gives `storage_path`
  and the bucket is private to the owning farmer. When photos exist the panel would still be empty, which is misleading.
  **GAP:** a signed-URL endpoint for experts. Until then, show "Photos exist but can't be displayed yet", not "No photos".
* Reason tags: only 3 reasons are designed ("Treatment question", "Farmer asked for expert", "Low photo confidence"). The backend also
  produces `models_conflict`, `label_unknown`, and `sources_unavailable:*`. Need tags (and Marathi names if shown to farmers).
* Submit-button labels and helper text for the other three decisions; the Category list (the 5 `Category` values and their display
  names, probably "unknown" excluded); validation messages (likely without a category, request_more without notes); success state after
  submit (the case leaves the pending list, toast, next case); submit error states for **409** (already reviewed) and **404/422**.
* The 403 screen still shows the expert nav, the **Expert** badge and "Metrics" tab for an account that is **not** an expert. It should use a non-expert shell
  (brand + Sign out only).
* Missing: the **Awaiting farmer / Follow-up received / Reviewed** views of the detail panel (read-only review result, the
  farmer's answer and photo, the escalation history); a queue **sort** and **search**; **pagination** (the API returns all rows);
  a **mobile or tablet** layout (only 1440 shown); notes character-limit and unsaved-draft behaviour; confirmation before sending; audit
  trail view (`audit_events` has no read endpoint).
* The warning about doses is advice only. Nothing blocks a dose in the notes (the backend does not filter expert text).
* "Sources: No verified source found." works, but the filled state (sources with verified, stale, structured flags) is not shown.

---

## 08 · Metrics dashboard

**Purpose:** show how the orchestrator behaves: routes taken, latency, cost, escalation and abstention, and what routing
skipped. **Role:** expert (the backend does not allow farmers; there is no separate admin role). **Viewport:** desktop 1440.
**Files:** `screenshots/08-metrics-dashboard/`

| File | State |
|---|---|
| `metrics-dashboard-default-en.png` | All-time data (3 analyses, 3 cases) |
| `metrics-dashboard-empty-no-analyses-en.png` | "Last 7 days": 0 analyses |
| `metrics-dashboard-error-session-expired-en.png` | 401 token expired |
| `metrics-dashboard-loading-en.png` | Skeletons |

**Layout (default)**
1. Top nav (as above, **Metrics** active).
2. Title **Orchestration metrics**; subtitle "All time · 3 analyses from 3 cases · generated 01 Oct 2026, 02:01 IST"; window pills **7 days / 30 days / 90 days / All time**.
3. KPI row 1 (5 cards): **ANALYSES** 3 ("3 distinct cases"); **LATENCY P50 / P95** "55 / 187 ms" ("avg 80.7 ms · max 187 ms");
   **COST PER CASE** $0.0000067 ("Total $0.00002 · estimated, not billed"); **SENT TO EXPERT** 33% ("1 of 3 analyses");
   **NO GUIDANCE GIVEN** 33% ("1 of 3 · abstention rate").
4. KPI row 2 (4 cards): **VISION ABSTAINED** 0% ("0 of 1 vision runs"); **RETRIEVAL SUCCESS** 50% ("1 of 2 lookups verified and
   current"); **WEATHER CACHE HITS** 0% ("0 of 1 · sources: live 1"); **MODEL DISAGREEMENT** 0 ("Only one vision model deployed").
5. **Route distribution** table (PATH, SHARE bar, AVG LATENCY, AVG COST, OUTCOME badge) with "Vision called in 1 of 3";
   **Decision states** bar list (all five states, zeros included) with "By question type: crop_health_image 1 · weather_context 1 · treatment_safety 1".
6. **Cost and latency by step** table (STEP, TIER, CALLS, ERRORS, P50, P95 with bar, TOTAL COST, AVG COST).
7. **Usage by tier** (small model / vision model / tool / large model "None yet", each with a calls bar and a cost bar and a legend)
   and **What routing skipped** (ESTIMATED COST SAVED $0.00004; IF VISION ALWAYS RAN $0.00006 "vs $0.00002 actual"; bar list of skipped steps).
8. **NOTES** panel with the two explanatory notes.

The default screenshot uses the same numbers as real output from the seeded backend (it matches the example in API.md).

**States**
* Empty (7-day window, no data): KPI cards show "0" or "—" with "No analyses to time", "Total $0", "0 of 0", then a dashed card "No analyses in the last 7 days" "Routes,
  step costs and latencies appear once farmers run crop checks. Try a longer window to see earlier activity." + **Show all time**.
* Error: pink card **Your session has expired** "Metrics couldn't load because you've been signed out. Sign in again to see them." + **Sign in again** / **Try again**, code line
  `401 · Token expired · GET /api/metrics/overview, /routes, /cost-latency`.
* Loading: skeleton KPI cards and two skeleton chart cards; "Loading metrics…"; the window pills stay interactive.

**API** (all three are expert-only and accept `?days=7|30|90`; omit `days` for All time)
| UI | Call | Fields |
|---|---|---|
| Subtitle and KPI row 1 and 2 | `GET /api/metrics/overview` | `window`, `total_analyses`, `total_cases`, `latency_per_analysis` {`p50_ms`, `p95_ms`, `avg_ms`, `max_ms`}, `cost_per_case_usd`, `cost_total_usd`, `escalation_rate`, `abstention_rate`, `vision_abstention_rate`, `retrieval_success_rate`, `cache_hit_rate`, `weather_sources`, `model_disagreement_count`, `decision_states`, `notes` |
| Route distribution, intent footer, "vision called in", skipped steps, cost saved | `GET /api/metrics/routes` | `by_path[]` {`path`, `count`, `share`, `avg_latency_ms`, `avg_cost_usd`, `decision_states`}, `by_intent`, `by_decision_state`, `vision_call_rate`, `skipped_steps`, `estimated_cost_saved_usd` |
| Cost and latency by step, usage by tier, if-vision-always-ran | `GET /api/metrics/cost-latency` | `by_step[]`, `by_tier[]` (`small_model` / `vision_model` / `large_model` / `tool`), `cost_total_usd`, `cost_if_vision_always_ran_usd`, `notes` |

Each rate is `{numerator, denominator, rate}` and `rate` is `null` when there is no data, which is how "—" in the empty state
should be driven.

**GAPS and MISSING**
* The API's `by_decision_state` only includes states that occurred. The design lists all five with zeros, so fill the zeros on the client.
* "Large model: None yet" needs a rule: show it when `calls = 0`.
* **Defaults differ:** the empty design is on "7 days" and the others on "All time". Pick one default (the API default is all time).
* Missing: partial failure (one of the three calls fails); a 403 version for a non-expert (the nav shows "Metrics" to an expert
  only, but the page itself needs the error state of screen 07); refresh and "last updated" control; export;
  a time-series chart (the API has no time series, so the design correctly has none); **mobile or tablet** layout;
  how long monospace route names wrap; very small numbers like `$0.0000067` need a stated formatting rule; Marathi.
* CLAUDE.md fixes **Recharts** for charts. The design draws plain bars; either is fine, but pick one.
* The note that the seeded demo images are synthetic does not appear. If the dashboard is shown with seeded data in a demo, say so on screen.

---

## Cross-cutting issues (apply to every screen)

1. **No Marathi anywhere.** 28 of 28 screenshots are English. The toggle labels exist (login, new-check "Answer in"), but no
   Marathi layout, copy or typography was designed. MVP scope is English **and** Marathi.
2. **The backend does not localize.** `CaseCreate.language` ("en" or "mr") is stored and passed to the orchestrator but **never
   used**: every `message`, `follow_up_question`, quality tip and weather summary is English. The frontend must therefore build
   user-facing text from **structured fields** (`state`, `reason`, `preliminary_label`, confidence band, `next_action`,
   `issues`) through its own English and Marathi i18n catalogue, and never print the backend's `message` for Marathi users. Intent
   keywords are bilingual, but answers are not.
3. **Two language concepts, one control.** "UI language" (the login toggle) and "Answer in" (the case's `language`) are
   separate in the design but look the same. Decide whether they are one setting.
4. **Placeholder content shown as real** (Result issue 1) and **dates that are retrieval times** (Result issue 2).
5. **Progress cannot be live** with the synchronous API (Analysis progress, "Mid-run").
6. **A mandatory photo contradicts the orchestrator's text-only routes** (New crop check).
7. **State coverage is thin.** Each screen has default, empty, error and loading, but the real outcomes are many more: 5 decision
   states × 7 routes for the farmer, 4 expert statuses, 4 decisions, and the weather source variants. See each screen's MISSING list.
8. **Error states cover network and auth only.** Expected API errors (404 not your case or not analyzed, 409, 413, 415, 422, 503) mostly have no design.
9. **Accessibility:** form-control border contrast 2.47:1 (needs 3:1); no focus, hover or keyboard states; tap-target sizes are fine.
10. **No dark mode, no tablet widths, no landscape, no offline state.**
