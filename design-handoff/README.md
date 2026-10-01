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

No frontend code was written, and nothing outside `design-handoff/` was changed.
