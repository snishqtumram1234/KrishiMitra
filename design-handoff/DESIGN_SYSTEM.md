# KrishiMitra design system (extracted from screenshots)

Source: 28 PNG screenshots exported from Claude Design. **No HTML, CSS or Figma data exists**, so everything here is
read off the pictures.

How to read the confidence labels in this document:

| Label | Meaning |
|---|---|
| **sampled** | A pixel colour read directly from a screenshot (exact for that element). The token *names* are my suggestion. |
| **approximate** | Measured or judged from the picture (sizes, radii, fonts, spacing). Confirm against the designer before treating it as final. |
| **not shown** | Nothing in the screenshots covers it. Do not invent it silently; ask or decide explicitly. |

Screenshot scale: mobile screens are 780 px wide (= **390 CSS px at 2x**). Desktop screens are 2880 px wide (= **1440 CSS px
at 2x**). All CSS sizes below are image pixels ÷ 2.

Screens seen: farmer screens are mobile only (390). Expert and metrics screens are desktop only (1440). See
[SCREENS.md](SCREENS.md).

---

## 1. Colour

The look is a **warm cream canvas, deep forest green, and near-black green ink**. Status colours come in soft tint
pairs (background + dark text) of green, amber, red and blue.

### 1.1 Neutrals and ink (sampled)

| Token (suggested) | Hex | Seen on |
|---|---|---|
| `canvas` | `#F6F4EC` | Page background, mobile app bar |
| `surface` | `#FDFCF7` | Cards, active tab, bottom sheet, desktop top bar (looks the same or slightly lighter) |
| `field` | `#FFFFFF` | Input and textarea background |
| `sunken` | `#ECE9DE` | Inactive tab track, disabled input, neutral pills, notes panel, "Not checked yet" badge |
| `skeleton` | `#E4E0D2` | Loading skeleton bars (also the unfilled part of bars: `#E4E0D1`) |
| `line` | `#D9D6C8` | 1 px card borders |
| `line-strong` | `#A9A594` | Input borders, empty pending-step circle, dashed empty-state borders |
| `disabled-fill` | `#D4D0C1` | Disabled primary button |
| `ink` | `#17231B` | Headings, selected filter chip, active language toggle, dark safety note |
| `ink-muted` | `#4A5A4F` | Secondary text, uppercase eyebrow labels, monospace code text |

### 1.2 Brand green (sampled)

| Token | Hex | Seen on |
|---|---|---|
| `brand` | `#1F5B3A` | Primary buttons, completed step icons and the line between them, outline button borders and text, links, selected chips, the 2 px "Next step" card border |
| `brand-soft` | `#46775B` | Partially filled timeline line (approx. a lighter step of the same green) |
| `brand-loading` | `#3F7255` | Primary button while loading ("Signing in…") |
| `brand-tint` | `#E3EDDF` | Success badges ("Live", "Guidance ready", "Preliminary guidance", "Verified", "Working") |
| `brand-wash` | `#F1F6EE` | Selected queue row and selected decision card background (a green border `#1F5B3A` goes with it) |

### 1.3 Status colours (sampled)

| Role | Background | Text / icon | Where |
|---|---|---|---|
| Success | `#E3EDDF` | `#1F5B3A` | Live weather, guidance ready, verified |
| Warning (amber) | `#F7E9CC` | text `#7A4700`, deep title `#5E3700` | "Needs photo", "Old reading", "Pending review", "Required", add-a-photo card, warning step icon |
| Error | `#F8E1DC` (badge, banner); error cards look slightly lighter, about `#FBEFED` (approximate) | text `#8F2217`, icon / border `#A3261B` | Error cards, "Low photo confidence", invalid input border |
| Info / expert (blue) | `#E2EAF5` | text `#1D4F8C`, deep title `#163D6D` | "Sent to expert", "With an expert", "Expert" badge, expert-decision card, blue button `#1D4F8C` |
| Accent amber | n/a | `#B98A2E` | Medium-confidence bar segment, cost bars |
| Dark note | `#17231B` | text white, icon `#E9C46A` | Safety note |
| Scrim | about `rgba(23,35,27,0.5)` (approximate) | n/a | Behind the upload bottom sheet |

**"Soil brown":** there is no separate brown brand colour. Browns appear only inside the amber family
(`#5E3700`, `#7A4700`, `#B98A2E`). The warm cream neutrals carry the earthy feel. If you expected a soil-brown brand
colour, it was not in the export.

### 1.4 Confidence-band colours

| Band | Range (matches backend thresholds) | Colour |
|---|---|---|
| Low | under 0.60 | **not shown active.** Only the inactive track `#E4E0D1` is visible. |
| Medium | 0.60 to 0.85 | `#B98A2E` (sampled) |
| High | above 0.85 | **not shown active.** Inactive track only. |

The bar is split into three segments (Low is the widest, Medium next, High the shortest, roughly proportional to the
ranges). A black triangle marker sits above the current value, and only the active band is coloured.
**Proposal, needs design sign-off:** Low = the error red family (`#A3261B`), High = `brand` green. Do not ship those
two without confirming.

### 1.5 Badge to state mapping seen in the designs

| Badge text | Colour | Meaning |
|---|---|---|
| Guidance ready / Preliminary guidance | success | `PRELIMINARY_GUIDANCE` |
| With an expert / Sent to expert | info (blue) | `EXPERT_REVIEW` |
| Needs photo | warning | `NEEDS_BETTER_IMAGE` (missing photo) |
| Working | success tint + spinner | analysis running |
| Starting | neutral + spinner | analysis starting |
| Not checked yet | neutral | case not analyzed |
| Live / Old reading | success / warning | weather source (`live` / stale `cached`) |
| Pending review | warning | expert status `pending_review` |
| Treatment question / Farmer asked for expert / Low photo confidence | warning / info / error | expert-queue reason tags |
| Expert | info | signed-in role |

States with **no badge designed** are listed in [SCREENS.md](SCREENS.md).

### 1.6 Contrast check (computed from the sampled hex values)

Text pairs all pass WCAG AA (4.5:1 or more): ink on canvas 14.8, muted on canvas 6.7, white on brand 8.0, white on
loading-green 5.6, brand on success tint 6.7, amber text on amber tint 6.4, red on red tint 7.0, blue on blue tint 6.8.

**Weak spots to fix when building:**

| Pair | Ratio | Problem |
|---|---|---|
| `line-strong` `#A9A594` input border on white | **2.47** | Below the 3:1 needed for a form-control boundary (WCAG 1.4.11). Darken the border, about `#7F7B6B` or darker. |
| Medium-confidence bar `#B98A2E` on its track `#E4E0D1` | **2.36** | Hard to tell apart for low-vision users. The marker and the "Medium · 0.65" text help, but add a pattern, outline or darker amber. |
| Card hairline `#D9D6C8` on surface | 1.42 | Decorative, so acceptable, but cards then rely on the colour difference to canvas. |
| Disabled text on disabled button | about 3.3 (the text colour is a guess) | Disabled controls are exempt, but keep them legible. |

Status is never colour-only: every badge and banner has words (and usually an icon), which is good.

---

## 2. Typography

Font identification from PNGs is a judgement call. **Approximate and unconfirmed: ask for the real font names.**

| Role | What it looks like | Closest free options to try first |
|---|---|---|
| Display / headings | Heavy (about 600 to 700), tightly tracked geometric grotesque. A single-storey `g`, straight-tailed `y`, hooked `f`. | Bricolage Grotesque, Hanken Grotesk or Schibsted Grotesk |
| Body / UI | Friendly humanist sans, regular 400 and 500 to 600 for labels | Mukta (also covers Devanagari, so Latin and Marathi match) |
| Code / technical strings | Monospace with a slashed or dotted zero (route names, model names, `0 ms`, `$0.00002`) | IBM Plex Mono or JetBrains Mono |

**Marathi rendering.** The only Marathi text in the whole export is the toggle label **मराठी** (a medium-weight
Devanagari face). No screen is shown in Marathi, so how headings, body, badges, long sentences and the monospace
strings render in Marathi is **not shown**. The heading font above is Latin-only, so Marathi headings need a
Devanagari-capable heading face (Mukta 700 or Noto Sans Devanagari 700) chosen deliberately. Use `next/font` with the
`devanagari` subset. Allow roughly 15 to 25 % more line height for Devanagari so matras do not clip.

### 2.1 Type scale (approximate)

| Style | Size / line-height | Weight | Used for |
|---|---|---|---|
| Hero | 34 to 36 px / 1.1 | 700 | Login headline "Check your soybean crop from a photo." |
| Page title | 28 to 30 px / 1.15 | 700 | "Your crop checks", "Review queue", "Orchestration metrics" |
| Result headline | 30 to 32 px / 1.1 | 700 | "Rust-like signs", "23°C" (weather is larger, about 56 px) |
| Top-bar title | 20 px | 600 | "Crop check result", "New crop check" |
| Section heading | 20 to 22 px | 600 to 700 | "1 · Leaf close-up", "What's happening?", "Missing information" |
| Step / card title | 18 to 20 px | 600 | Progress step names, case titles |
| Body | 15 to 16 px / 1.4 to 1.5 | 400 | Paragraphs, descriptions |
| Label | 15 px | 600 | Form labels |
| Helper / caption | 13 to 14 px | 400 | Hints, counters ("22 / 2000"), timestamps |
| Eyebrow label | 12 to 13 px, UPPERCASE, tracking about 0.08 em | 600 to 700 | "POSSIBLE CONDITION", "PUNE WEATHER", table headers |
| Monospace | 13 to 14 px | 400 | `intent_router`, model names, error code lines |
| KPI number | 36 to 44 px | 700 | Metric cards ("55 / 187 ms") |
| Button | 17 to 18 px | 600 | All buttons |

---

## 3. Spacing, radius, borders, shadows (approximate)

* **Base unit 4 px.** Mobile gutter **16 px**; desktop page gutter about **32 px**. Card padding **16 to 20 px**.
  Gap between stacked cards about 16 to 20 px; between sections about 24 to 32 px.
* **Radius:** cards 16 to 18 px; bottom sheet top corners about 24 px; buttons and inputs about 14 px; thumbnails 12 to
  14 px; chips, badges and pills fully rounded (999 px).
* **Heights:** primary button about **52 px** (full width on mobile); inputs about **48 px**; filter chips and
  quick-reply chips about 40 to 44 px; top bar about 60 px.
* **Borders over shadows.** The UI is essentially flat. Cards are `surface` + 1 px `line` border. The only shadow is a
  very soft one under the active segmented-tab (about `0 1px 2px rgba(0,0,0,0.08)`, approximate).
* **Emphasis card:** 2 px `brand` border (the "Next step" card).
* **Empty-state card:** 2 px dashed `line-strong` border (empty lists, upload boxes, "nothing selected").
* **Icons:** line icons, about 2 px stroke, rounded caps (leaf, camera, user, shield, magnifier, bar-chart,
  alert-circle, check-circle, chevrons, calendar). Brand mark is a leaf outline.

---

## 4. Controls

### Buttons

| Variant | Look |
|---|---|
| Primary | Filled `brand`, white text, radius 14, height 52. Full width on mobile. Optional leading icon (camera). |
| Secondary | Transparent or surface fill, 2 px `brand` border, `brand` text. Used for "Try again", "Retake", "From gallery", "My checks". |
| Info (expert) | Filled `#1D4F8C`, white text (the "Go to my checks" button inside the expert-sent card). |
| Filter chip | Pill, 1.5 px `line-strong` outline, ink text. **Selected:** filled `ink`, white text, optional count ("Pending review · 3"). |
| Quick-reply chip | Pill with 2 px `brand` outline. **Selected:** filled `brand`, white text. |
| Disabled | Fill `#D4D0C1`, muted text (the empty "Check my crop" button). |
| Loading | Fill `brand-loading`, spinner + "Signing in…". Inputs become `sunken`. |
| Link | `brand`, underlined ("Forgot password?"). |
| Header sign-out | Outline pill, `brand` border. |

### Inputs

* Text input / select / date: `field` white, 1 to 1.5 px `line-strong` border, radius 14, height 48.
* Textarea has a right-aligned counter ("22 / 2000"). Date input is the native control with a calendar icon.
* Error: border `#A3261B`, helper text in red below. Disabled: `sunken` fill.
* Locked field (crop = Soybean): `sunken` fill, same shape as an input, with the helper "KrishiMitra covers soybean in
  Maharashtra for now."
* Label above the field, 15 px / 600. Optional or required is a pill at the section heading, not on the field.
* **Not shown:** focus ring, hover state, placeholder text colour for disabled, password show/hide, select dropdown
  open state.

### Segmented controls

* **Tabs** (Sign in | Create account): `sunken` track, active tab is `surface` with the soft shadow.
* **Language toggle** (English | मराठी): 2 px `line-strong` outline pill, active side filled `ink` with white text.
  The same control appears in the login header and as "Answer in" on the new-check form.

### Feedback

* **Inline field error** under the field. **Error summary** banner at the top of a form, listing each problem as an
  underlined jump link ("2 things to fix before we can check").
* **Error card** (pink): alert-circle icon + bold red title + explanation + "Try again" + a muted monospace line with the
  HTTP status ("403 · Expert role required").
* **Empty-state card:** dashed border, large icon, bold title, short text, one clear action.
* **Skeletons:** `skeleton`-coloured rounded bars and blocks that mirror the real layout, plus a short caption
  ("Loading your checks…"). No shimmer animation is visible in a still image (animation **not shown**).

---

## 5. Reusable components

Names are suggestions for the Next.js build. "Data" says where the real values come from (see [SCREENS.md](SCREENS.md)).

| Component | What it is | Data |
|---|---|---|
| `AppBar` (mobile) | Leaf logo + wordmark with a user icon; or back arrow + page title | none |
| `TopNav` (desktop, expert) | Logo, tabs "Review queue" / "Metrics" (active = `brand-tint` pill), "Expert" badge, "Sign out" | role from JWT |
| `LanguageToggle` | English / मराठी segmented control | UI locale and `CaseCreate.language` |
| `AuthTabs`, `TextField`, `PasswordField`, `Textarea`, `Select`, `DateField` | Form primitives | Supabase Auth / `CaseCreate` |
| `Button` | primary, secondary, info, chip, link, disabled, loading | none |
| `StatusBadge` | Tinted pill (success, warning, error, info, neutral) with optional spinner | `decision_state`, expert `status`, weather `source` |
| `WeatherCard` | District eyebrow, source badge, big temperature, rain next 24 h, chance, humidity, wind, provenance line | `GET /api/weather` |
| `CaseListItem` | Question title, status badge, "District · stage · time" | `GET /api/cases` |
| `ImageUploadBox` | Empty (dashed: Take photo / From gallery / format hint) and filled (thumbnail, filename, "JPEG · 205 KB", Ready or Not uploaded pill, Retake). A compact optional variant for the field photo. | local file, then `POST .../images` |
| `FormSection` | Numbered heading ("1 · Leaf close-up") with a Required or Optional pill | none |
| `ErrorSummary` | Pink banner with a list of jump links | client validation, API 422 |
| `UploadProgressSheet` | Bottom sheet: "Sending your check", 3-step checklist, byte progress bar ("140 of 205 KB"), "Keep this screen open…" | upload progress |
| `RouteTimeline` | Vertical stepper: done, active (spinner), pending, skipped (dashed circle + struck-through title), failed (red cross), warning (amber "!"), decided (blue check). Right-aligned latency, monospace "step · model" line. | `result.calls`, `route_trace`, `skipped_steps` |
| `RouteBanner` | "ROUTE · image_diagnosis" eyebrow + one-sentence plain explanation | `result.path` |
| `QuestionSummaryCard` | Thumbnail (or dashed empty), question title, "Pune · R3 · close-up photo" | case |
| `PossibleConditionCard` | Eyebrow, headline, disclaimer sentence, divider, `ConfidenceBand`, explanation | `preliminary_label`, `confidence` |
| `ConfidenceBand` | 3-segment bar, black triangle marker, "Medium · 0.65", labels "Low · under 0.60 / Medium / High" | `confidence`, thresholds 0.60 / 0.85 |
| `EvidenceCard` ("What we observed") | Thumbnail + photo-check line + key-value rows (Leaf reader, You noticed, Growth stage, Started, Recent rain) | quality call output, vision call, case |
| `MissingInfoList` | Numbered rows; the first has an amber circle, the others neutral | derived (see SCREENS.md) |
| `SourceCard` | Title, "Publisher: …", pills (Verified, Up to date, General text), "Retrieved <date>" | `result.sources` |
| `NextStepCard` | Emphasis card: question, quick-reply chips, optional detail input, "Send answer", "Add field photo" | `follow_up_question`, `POST .../follow-up` |
| `SafetyNote` | Dark card, amber shield icon, "Safety note. KrishiMitra never gives pesticide names or doses…" | static copy |
| `RouteDetailsAccordion` | "Route details" with Hide/Show; key-values (Question type, Rule, Path, Decision, Total) + per-step rows (mono step, model · extra, ms, $) | `GET /api/runs/{id}` |
| `ExpertSentCard` / `NeedsPhotoCard` | Tinted result cards with title, text, one button, and a monospace state code line | `state`, `reason` |
| `FilterChips` | Row of pills with an optional count | queue statuses / metrics window |
| `QueueItem` | Title, date, reason tag + district tag; selected variant | `GET /api/expert/cases` |
| `CaseDetailPanel` | Meta grid, Missing information, Photos, Sources, Farmer follow-ups, Model predictions table, review form | `GET /api/expert/cases/{id}` |
| `DecisionRadioCards` | 4 radio cards with a title and one-line hint; selected = green border and wash | `ReviewIn.decision` |
| `MetricCard` | Eyebrow label, big value, one-line detail | `/api/metrics/overview` |
| `DataTable` | Eyebrow header row; rows with monospace first column, inline bar, outcome badge | `/routes`, `/cost-latency` |
| `BarList` | Label (mono), horizontal bar, right-aligned count | decision states, skipped steps |
| `TierUsage` | Per tier: two bars (share of calls in green, share of cost in amber) with a legend | `/cost-latency` `by_tier` |
| `NotesPanel` | `sunken` panel with bulleted notes | `notes[]` |
| `EmptyState`, `ErrorState`, `Skeleton*` | See section 4 | none |

The metrics charts are drawn as simple CSS bars. CLAUDE.md fixes **Recharts** in the stack, so build the bars either
with plain Tailwind (as designed) or with Recharts `BarChart`, but keep one approach.

---

## 6. Layout rules and breakpoints

**Farmer app: mobile first, 390 px design width.**
Single column, 16 px gutters, cards stacked full width, primary actions full width and thumb-reachable at the bottom
of a card or screen. Top bar either shows the brand + user icon (dashboard) or a back arrow + title (inner pages). No
bottom tab bar is shown. Long pages scroll (new-check form is about 1,400 px tall, result about 2,240 px).

**Expert and metrics: desktop, 1440 px design width.**
Top nav bar (about 64 to 68 px tall) then content with about 32 px gutters. Expert queue is two columns: a queue
(about 480 px, roughly 35 %) and a detail panel (about 860 px, roughly 60 %). Metrics is a 5-column KPI row, then a 4-column row,
then two-column chart rows, then a full-width table, then a full-width notes panel.

**Breakpoints (inferred, only two widths are shown):**

| Width | Evidence | Build as |
|---|---|---|
| 390 px | All farmer screens | base styles (no prefix), designed for 360 to 430 |
| 1440 px | All expert and metrics screens | `xl:` layout (suggest 1280), with `lg` (1024) as the earliest two-column |

**Not shown, so decide before building:** farmer screens above 390 px (suggest a centred `max-w-md` column);
expert and metrics screens below about 1024 px (tablet and phone); landscape orientation; any print layout.

Targets: buttons 52 px and inputs 48 px tall meet the usual 44 px touch minimum. Keep that on the build.

---

## 7. Suggested Tailwind theme extension

Written for Tailwind v3 syntax (it works in v4 through `@config`, or translate to `@theme`). Hex values are the
**sampled** ones above. Fonts are placeholders until the real font names are confirmed, and are set from
`next/font` CSS variables.

```ts
// tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#F6F4EC",
        surface: "#FDFCF7",
        field: "#FFFFFF",
        sunken: "#ECE9DE",
        skeleton: "#E4E0D2",
        line: { DEFAULT: "#D9D6C8", strong: "#A9A594" }, // darken strong to ~#7F7B6B for 3:1 (see 1.6)
        ink: { DEFAULT: "#17231B", muted: "#4A5A4F" },
        brand: {
          DEFAULT: "#1F5B3A",
          soft: "#46775B",
          loading: "#3F7255",
          tint: "#E3EDDF",
          wash: "#F1F6EE",
        },
        success: { bg: "#E3EDDF", fg: "#1F5B3A" },
        warning: { bg: "#F7E9CC", fg: "#7A4700", deep: "#5E3700", accent: "#B98A2E", glow: "#E9C46A" },
        danger: { bg: "#F8E1DC", card: "#FBEFED", fg: "#8F2217", solid: "#A3261B" }, // card is approximate
        info: { bg: "#E2EAF5", fg: "#1D4F8C", deep: "#163D6D" },
        // Confidence bands. Only `medium` was sampled; low/high are PROPOSED (confirm with design).
        band: { low: "#A3261B", medium: "#B98A2E", high: "#1F5B3A", track: "#E4E0D1" },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"], // approximate: a geometric grotesque
        sans: ["var(--font-body)", "var(--font-devanagari)", "system-ui", "sans-serif"], // approximate: Mukta-like
        mono: ["var(--font-mono)", "ui-monospace", "monospace"], // approximate: IBM Plex Mono-like
      },
      fontSize: {
        hero: ["2.125rem", { lineHeight: "1.1", fontWeight: "700" }],
        title: ["1.75rem", { lineHeight: "1.15", fontWeight: "700" }],
        headline: ["1.875rem", { lineHeight: "1.1", fontWeight: "700" }],
        heading: ["1.25rem", { lineHeight: "1.25", fontWeight: "600" }],
        body: ["1rem", { lineHeight: "1.5" }],
        caption: ["0.875rem", { lineHeight: "1.4" }],
        eyebrow: ["0.75rem", { lineHeight: "1.2", letterSpacing: "0.08em", fontWeight: "700" }],
        code: ["0.8125rem", { lineHeight: "1.4" }],
        kpi: ["2.25rem", { lineHeight: "1.05", fontWeight: "700" }],
      },
      borderRadius: { card: "18px", control: "14px", sheet: "24px" }, // approximate; pill = rounded-full
      height: { control: "48px", button: "52px" },
      boxShadow: { segment: "0 1px 2px rgba(0,0,0,0.08)" }, // approximate
      screens: { sm: "640px", md: "768px", lg: "1024px", xl: "1280px" },
    },
  },
  plugins: [],
};
export default config;
```

```ts
// app/layout.tsx (fonts: replace with the confirmed families)
import { Mukta, IBM_Plex_Mono, Bricolage_Grotesque } from "next/font/google";

const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display" });
const body = Mukta({ subsets: ["latin", "devanagari"], weight: ["400", "500", "600", "700"], variable: "--font-body" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });
```

---

## 8. Open items for the designer

1. Real font names and a Devanagari-capable heading face.
2. Low and High confidence-band colours (only Medium is shown).
3. Darker input border and a pattern or darker amber for the confidence bar (contrast, section 1.6).
4. Focus, hover, pressed and keyboard states (none shown), and dark mode (none shown).
5. Tablet and phone layouts for expert and metrics; desktop layout for the farmer app.
6. Shimmer or animation spec for skeletons, spinners and step transitions.
