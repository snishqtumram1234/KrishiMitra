# Design handoff

Prototype screenshots of the KrishiMitra interface, exported from Claude Design, plus the documents needed to rebuild
them in the real app.

## What this is (and is not)

* **These are screenshots of a prototype, not production code.** There is no HTML, CSS or Figma source. Every colour,
  size and font in [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) was read off the images (colours sampled from pixels, the rest
  measured or judged and labelled *approximate*).
* **The data in the screenshots is example data.** Some of it (for example the 3-analysis metrics and "Which pesticide and
  how much?") happens to match real backend output, but nothing here is a source of truth. The contract is
  [API.md](../API.md).
* **Do not copy anything from the prototype into the app.** Rebuild it.

## How it must be rebuilt

1. **Next.js + TypeScript + Tailwind components** (the fixed stack in [CLAUDE.md](../claude.md)); Recharts if charts are
   needed. Build the components listed in [DESIGN_SYSTEM.md §5](DESIGN_SYSTEM.md#5-reusable-components) and the screens in
   [SCREENS.md](SCREENS.md).
2. **No mock data.** Every number, status, label and list comes from the backend or from the user's input. Where the
   screenshots show a value the API cannot supply today, SCREENS.md marks it **GAP**; resolve it in the backend or change
   the screen, but do not hard-code a stand-in.
3. **All backend calls go through one module: `lib/api-client.ts`.** It attaches the Supabase access token
   (`Authorization: Bearer`), sets the base URL, parses the error shapes in API.md, and exposes one typed function per
   endpoint. Components and pages never call `fetch` directly. (Supabase Auth sign-in itself is the one thing that talks to
   Supabase rather than the backend.)
4. **Frontend copy comes from i18n catalogues (English and Marathi), built from the API's structured fields**, not from
   the backend's English `message` strings (the backend does not localize; see SCREENS.md, cross-cutting issues).
5. **Keep the safety rules visible:** every image-based answer is a *preliminary observation, never a confirmed
   diagnosis*, and the app never shows pesticide names or doses.

## Folder contents

```
design-handoff/
├── README.md            this file
├── DESIGN_SYSTEM.md     colours, type, spacing, controls, components, breakpoints, Tailwind theme
├── SCREENS.md           per-screen spec: layout, text, states, API mapping, missing states, design issues
└── screenshots/         28 PNGs, 2x resolution (mobile 780 px = 390 CSS px, desktop 2880 px = 1440 CSS px)
    ├── 01-landing/             0   (none provided; contains only .gitkeep)
    ├── 02-auth/                4   sign in, create account
    ├── 03-farmer-dashboard/    4   mobile
    ├── 04-new-crop-check/      4   mobile
    ├── 05-analysis-progress/   4   mobile
    ├── 06-result/              4   mobile
    ├── 07-expert-dashboard/    4   desktop
    └── 08-metrics-dashboard/   4   desktop
```

Every screen that exists has the same four states: default, empty, error, loading. All are **English only**; there is no
Marathi screenshot. File names are `<screen>-<state>-<language>.png`, lowercase with hyphens.

### Where each exported file went

The files were exported with names like `Result · Default.png`. They were moved (not copied, nothing deleted or altered;
checked byte for byte) as follows.

| Original name | Now |
|---|---|
| Login · Default | `02-auth/auth-sign-in-default-en.png` |
| Login · Empty (new account) | `02-auth/auth-create-account-empty-en.png` |
| Login · Error | `02-auth/auth-sign-in-error-wrong-password-en.png` |
| Login · Loading | `02-auth/auth-sign-in-loading-en.png` |
| Farmer dashboard · Default | `03-farmer-dashboard/farmer-dashboard-default-en.png` |
| Farmer dashboard · Empty | `03-farmer-dashboard/farmer-dashboard-empty-no-checks-en.png` |
| Farmer dashboard · Error | `03-farmer-dashboard/farmer-dashboard-error-load-failed-en.png` |
| Farmer dashboard · Loading | `03-farmer-dashboard/farmer-dashboard-loading-en.png` |
| New crop check · Default | `04-new-crop-check/new-crop-check-default-en.png` |
| New crop check · Empty | `04-new-crop-check/new-crop-check-empty-en.png` |
| New crop check · Error | `04-new-crop-check/new-crop-check-error-validation-en.png` |
| New crop check · Loading (submitting) | `04-new-crop-check/new-crop-check-loading-submitting-en.png` |
| Analysis progress · Default (mid-run) | `05-analysis-progress/analysis-progress-default-mid-run-en.png` |
| Analysis progress · Empty (no close-up) | `05-analysis-progress/analysis-progress-empty-no-closeup-en.png` |
| Analysis progress · Error (step failed) | `05-analysis-progress/analysis-progress-error-step-failed-en.png` |
| Analysis progress · Loading (starting) | `05-analysis-progress/analysis-progress-loading-starting-en.png` |
| Result · Default | `06-result/result-medium-confidence-en.png` |
| Result · Empty (not analyzed) | `06-result/result-empty-not-analyzed-en.png` |
| Result · Error | `06-result/result-error-load-failed-en.png` |
| Result · Loading | `06-result/result-loading-en.png` |
| Expert dashboard · Default | `07-expert-dashboard/expert-dashboard-default-en.png` |
| Expert dashboard · Empty | `07-expert-dashboard/expert-dashboard-empty-no-pending-en.png` |
| Expert dashboard · Error | `07-expert-dashboard/expert-dashboard-error-not-expert-en.png` |
| Expert dashboard · Loading | `07-expert-dashboard/expert-dashboard-loading-en.png` |
| Metrics dashboard · Default | `08-metrics-dashboard/metrics-dashboard-default-en.png` |
| Metrics dashboard · Empty | `08-metrics-dashboard/metrics-dashboard-empty-no-analyses-en.png` |
| Metrics dashboard · Error | `08-metrics-dashboard/metrics-dashboard-error-session-expired-en.png` |
| Metrics dashboard · Loading | `08-metrics-dashboard/metrics-dashboard-loading-en.png` |

Nothing was left unsorted, so there is no `screenshots/unsorted/` folder. The original `incoming/` folder was empty after the
move and was removed.

## Decisions needed before building

> **Status:** these were the open questions after the design review. They are answered in [Decisions](#decisions) below.
> The only one still open is the landing page.

Collected from SCREENS.md; each one blocks or changes a screen.

1. **Is the close-up photo mandatory?** The form says Required, which makes the weather, advisory, treatment, expert and general-question
   routes unreachable from the UI.
2. **Analysis progress:** show the real step timeline after the response (honest, no backend change), or add streaming and
   polling to the backend for a live "mid-run" view?
3. **Advisory source honesty:** the placeholder is flagged "verified" and the design shows a green "Verified". Source dates do not exist in the API.
4. **Marathi:** who writes and reviews the Marathi copy, and which Devanagari-capable heading font is used?
5. **Farmer "Missing information" and quick-reply chips** are not in the API response. Derive client-side or extend the API?
6. **Expert photo viewing** needs a signed-URL endpoint.
7. **Landing page:** does one exist (none was provided)?
8. **Confidence band colours** for Low and High, and the contrast fixes in DESIGN_SYSTEM.md §1.6.

## Not done here

When this handoff was first created, no frontend code was written and nothing outside `design-handoff/` was changed. Still true: no frontend code exists yet.

## Decisions

Recorded after the design review. **Where [SCREENS.md](SCREENS.md) or the screenshots disagree with a decision here, the decision
wins.** SCREENS.md still describes the prototype as exported (it lists several of these as gaps); it has not been rewritten.

### Product and backend decisions

Decisions 1 to 7 are implemented in the backend (commit `794783f`) and described in [API.md](../API.md).

1. **The photo is required only for the crop-health route.** There is a separate "ask a question" path with no photo (weather,
   advisory, expert, treatment safety), handled by the intent router: `POST /api/questions`. A crop-health question sent without
   a photo comes back as "needs a photo" and can be resumed on the same case.
   *For the frontend:* the New crop check form keeps its required photo. A new "Ask a question" entry point is needed, and **it has
   no design yet**.
2. **Progress is honest after the fact.** The frontend **replays the real recorded trace**. There is no streaming and no fake
   mid-run state. *For the frontend:* show the "starting" skeleton while the request is in flight, then replay the steps using each
   step's real `started_at_ms` and `latency_ms`. Do not invent timings or intermediate steps.
3. **Placeholder and demo sources are never verified.** They return `verified: false` and `source_type: "demo"`; only real
   ingested advisory documents may be `verified: true`. Sources carry `published_at`, `source_url` and `retrieved_at`, kept
   separate. *For the frontend:* show the green **Verified** pill only when `verified` is true; show a demo source as "Demo source, not
   verified"; show "Published" and "Retrieved" as two different dates, and hide whichever is null.
4. **Marathi copy is built in the frontend from structured fields**, through English and Marathi i18n catalogues. The backend does
   not localize; never print its English `message` or `follow_up_question` to a Marathi user.
5. **Structured fields on every response:** `missing_information` (list of codes), `follow_up_options` (`question_id` plus option
   codes), stable `reason_code` / `reason_detail`, and `confidence_band` (`low`, `medium`, `high`). The "Missing information" list
   and the "Older / Younger / Both" chips are built from these.
6. **Signed image links** for experts and the case owner: `GET /api/cases/{case_id}/images/{image_id}/signed-url`, valid for 5
   minutes. Image ids are in case and expert responses. *For the frontend:* request a fresh link when a photo is opened; never store
   or cache one.
7. **The analyze response includes the full trace** (every step, including skipped ones, with real timings) so the frontend can
   replay it.

### Design decisions

Applied in [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md); every contrast figure there is calculated from the hex values.

8. **Confidence-band colours:** Low `#A3261B`, Medium `#8A6212`, High `#1F5B3A`, each at least 3:1 against the track and the card
   (§1.4). The band is never colour-only: text label, segment position and marker always accompany the colour.
9. **A soil-brown brand colour:** a ramp with `soil-500` `#8A5A33` as the brand soil colour (§1.7). Brand only, never a status
   colour. Metrics cost bars use it instead of amber.
10. **Input and control borders at least 3:1:** `control-border` `#7F7B6B` (4.24:1 on white), replacing `#A9A594` (2.47:1) (§1.1, §1.6).
11. **A darker Medium-confidence bar at least 3:1:** `#8A6212` (4.14:1 on the track), replacing `#B98A2E` (2.36:1) (§1.4).
12. **Visible focus states:** a 3 px `#1D4F8C` ring with a 2 px offset on every interactive element (`#E9C46A` on dark panels), using
    `:focus-visible`, and never removed (§1.8).
13. **Noto Sans Devanagari for Marathi**, for all Marathi text, with a looser line height and no tracking or uppercase (§2.2).

### Still open

* **The landing page:** none was provided and no decision was recorded.
* **Who writes and reviews the Marathi copy**, and **Devanagari or Western digits** inside Marathi text.
* **The "Ask a question" screen** (decision 1 adds a path the prototype does not have).
* **The real Latin font names**, hover and pressed states, dark mode, tablet layouts and animation specs ([DESIGN_SYSTEM.md §8](DESIGN_SYSTEM.md#8-open-items-for-the-designer)).
* **Every state marked MISSING in [SCREENS.md](SCREENS.md)**, for example result variants other than medium confidence, expert-review
  success and error states, and progress copy for the non-image routes.
