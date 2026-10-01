# KrishiMitra design system (extracted from screenshots)

Source: 28 PNG screenshots exported from Claude Design. **No HTML, CSS or Figma data exists**, so everything here is
read off the pictures.

How to read the confidence labels in this document:

| Label | Meaning |
|---|---|
| **sampled** | A pixel colour read directly from a screenshot (exact for that element). The token *names* are my suggestion. |
| **approximate** | Measured or judged from the picture (sizes, radii, fonts, spacing). Confirm against the designer before treating it as final. |
| **not shown** | Nothing in the screenshots covers it. Do not invent it silently; ask or decide explicitly. |
| **DECIDED** | A product decision that **overrides** the screenshots where they differ. Contrast figures for these are calculated, not estimated. |

Screenshot scale: mobile screens are 780 px wide (= **390 CSS px at 2x**). Desktop screens are 2880 px wide (= **1440 CSS px
at 2x**). All CSS sizes below are image pixels ÷ 2.

**Decided changes to the prototype** (all marked **DECIDED** below): Low and High confidence-band colours (§1.4); a soil-brown
brand colour (§1.7); input and control borders at least 3:1 (§1.1, §1.6); a darker Medium bar at least 3:1 (§1.4); visible focus
states (§1.8); Noto Sans Devanagari for Marathi (§2.2).

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
| `line-strong` | `#A9A594` | **Decorative only now:** dashed empty-state borders, the empty pending-step circle. Below 3:1, so never use it for a control. |
| `control-border` | `#7F7B6B` **DECIDED** | Borders of every interactive control: text input, select, textarea, date, radio and checkbox, filter chips, language toggle. 4.24:1 on white, 4.13:1 on surface, 3.85:1 on canvas. Replaces `#A9A594` (2.47:1). |
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
| Accent amber | n/a | `#B98A2E` | Decorative amber accents only. **No longer** the Medium-confidence bar (now `#8A6212`, §1.4) or the cost bars (now soil brown, §1.7). |
| Dark note | `#17231B` | text white, icon `#E9C46A` | Safety note |
| Scrim | about `rgba(23,35,27,0.5)` (approximate) | n/a | Behind the upload bottom sheet |

**"Soil brown":** the screenshots had no separate brown brand colour (browns appeared only inside the amber warning family:
`#5E3700`, `#7A4700`, `#B98A2E`). **DECIDED:** add one, see §1.7. Amber stays reserved for warnings and the Medium band.

### 1.4 Confidence-band colours (DECIDED)

| Band | Range (matches backend thresholds) | Segment colour | vs track `#E4E0D1` | vs surface `#FDFCF7` | vs canvas `#F6F4EC` |
|---|---|---|---|---|---|
| Low | under 0.60 | `#A3261B` (the error red) | 5.57 : 1 | 7.17 : 1 | 6.69 : 1 |
| Medium | 0.60 to 0.85 | `#8A6212` (a darker amber) | **4.14 : 1** | 5.33 : 1 | 4.97 : 1 |
| High | above 0.85 | `#1F5B3A` (brand green) | 6.07 : 1 | 7.82 : 1 | 7.29 : 1 |

All three are at least **3:1** against the unfilled track and against the card behind it (WCAG 1.4.11). Medium was `#B98A2E`
in the screenshots (2.36:1 on the track, 3.03:1 on the card), which is replaced. The darker amber is still clearly amber, and it is
close to the warning text colour `#7A4700`, so the amber family reads as one idea.

How the bar is built (the Low segment is the widest, then Medium, then High, roughly proportional to the ranges):

* Only the **active band** is filled with its colour; the other two segments stay `#E4E0D1`.
* A black (`ink`) triangle **marker** sits above the exact value.
* The band is **never colour-only**: the text "Medium · 0.65" is shown, each segment has a text label ("Low · under 0.60", "Medium",
  "High"), and the segments always sit in the same left-to-right order. This matters because Low (red) and High (green) have almost
  the same lightness (1.09 : 1 apart), so people with red-green colour blindness cannot tell them apart by colour. Do not drop the
  labels or the marker.
* Use the same three colours for any band indicator elsewhere (expert prediction rows, metrics).

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

**Weak spots found in the screenshots, and how they are resolved:**

| Pair | Was | Now (DECIDED) |
|---|---|---|
| Input and control border on white | `#A9A594` = **2.47 : 1** (fails 3:1) | `control-border` `#7F7B6B` = **4.24 : 1** on white, 4.13 on surface, 3.85 on canvas |
| Medium-confidence bar on its track | `#B98A2E` = **2.36 : 1** | `#8A6212` = **4.14 : 1** on the track, 5.33 on surface |
| Card hairline `#D9D6C8` on surface | 1.42 : 1 | unchanged: decorative only (the card is separated from the canvas by fill and spacing, and nothing depends on seeing the line) |
| Placeholder text on white | unknown | use `#6B6F66` = 5.13 : 1 (recommended) |
| Disabled text on disabled button | about 3.3 (text colour was a guess) | exempt from WCAG, but keep it legible |

Every control border is `control-border`; `line-strong` is for decoration only. Rule for the build: **any new border or fill that
marks the edge of something clickable, typeable or selectable must be at least 3:1 against what is next to it.**

Status is never colour-only: every badge and banner has words (and usually an icon), which is good.

### 1.7 Soil brown brand colour (DECIDED)

A warm, desaturated earth brown that pairs with the forest green and the cream canvas. It is a **brand** colour, not a status colour.

| Token | Hex | On canvas | On surface | On track `#E4E0D1` | White text on it | Use |
|---|---|---|---|---|---|---|
| `soil-50` | `#F4ECE3` | n/a | n/a | n/a | n/a | tinted backgrounds (needs `soil-700` or darker text: 8.29 : 1) |
| `soil-100` | `#EADCCB` | n/a | n/a | n/a | n/a | tinted backgrounds, dividers |
| `soil-300` | `#BFA07F` | 2.23 | 2.39 | 1.86 | 2.46 | decoration only: never text, never a lone indicator |
| `soil-500` | `#8A5A33` | 5.31 | 5.69 | **4.42** | 5.85 | **the brand soil colour.** Chart series, icon fills, accent rules |
| `soil-600` | `#744B2A` | 6.85 | 7.35 | 5.71 | 7.55 | filled soil buttons or badges with white text |
| `soil-700` | `#5E3D22` | 8.80 | 9.44 | 7.33 | 9.69 | soil-coloured text |
| `soil-900` | `#3A2515` | 13.10 | 14.05 | 10.91 | 14.43 | darkest soil: illustrations |

Where it is used:

* **The logo's ground line:** the leaf mark stays brand green; a short soil-brown stroke under it.
* **Metrics cost bars** (and any "cost" series): use `soil-500` (4.42 : 1 on the track). They were amber `#B98A2E` in the screenshots,
  which wrongly suggested a warning. Calls bars stay `brand` green.
* **Source and advisory cards:** a 4 px `soil-500` left accent rule and a `soil-700` eyebrow. It marks "where this came from" visually
  apart from the green "result" and the amber "warning" cards.
* **Empty-state and onboarding illustrations:** soil under the leaf.
* **Never** for success, warning, error, "needs attention" or any state. A warning always uses the warning pair **plus an icon and
  words**, so soil and amber can never be mistaken for each other.

### 1.8 Focus states (DECIDED)

Every interactive element has a visible keyboard focus indicator. Use `:focus-visible` (keyboard focus), not `:focus`, so mouse
clicks do not draw a ring. **Never remove the outline** (`outline-none` is banned unless it is replaced by the ring below).

| Token | Hex | Contrast (calculated) |
|---|---|---|
| `focus` | `#1D4F8C` | 7.48 : 1 on canvas, 8.02 on surface, 8.24 on white, 6.78 on sunken, 6.84 on green tint, 6.86 on amber tint |
| `focus-on-dark` | `#E9C46A` | 9.72 : 1 on `ink` `#17231B` (the dark safety note and any dark panel) |

* **Ring:** `outline: 3px solid #1D4F8C; outline-offset: 2px;`. The 2 px gap puts the ring against the page, not the control's own
  fill, so it stays at least 3:1 on a green, ink or white control alike. A 3 px ring meets the 2 px minimum thickness of WCAG 2.2
  Focus Appearance (2.4.11).
* **Text inputs, selects, textareas, date fields:** the ring above **plus** the border turns `focus`. If the field is also in error,
  keep the red border and still show the blue ring.
* **Buttons, links, chips, tabs, the language toggle, radio cards, queue rows, accordions:** the ring above. Radio cards and queue
  rows (selected = green border) keep the selected styling and add the ring on top.
* **On dark surfaces** (the safety note, any dark panel): use `focus-on-dark`.
* **Disabled controls** are not focusable and show no ring.
* **Order and traps:** focus order follows reading order; the bottom sheet ("Sending your check") and any dialog trap focus and
  return it to the control that opened them.
* Hover and pressed states are still **not shown** in the prototype (see §8).

---

## 2. Typography

Font identification from PNGs is a judgement call. **Approximate and unconfirmed: ask for the real font names.**

| Role | What it looks like | Closest free options to try first |
|---|---|---|
| Display / headings | Heavy (about 600 to 700), tightly tracked geometric grotesque. A single-storey `g`, straight-tailed `y`, hooked `f`. | Bricolage Grotesque, Hanken Grotesk or Schibsted Grotesk |
| Body / UI | Friendly humanist sans, regular 400 and 500 to 600 for labels | Mukta or a similar humanist sans. **Latin text only; Marathi uses Noto Sans Devanagari (§2.2).** |
| Code / technical strings | Monospace with a slashed or dotted zero (route names, model names, `0 ms`, `$0.00002`) | IBM Plex Mono or JetBrains Mono |

**Marathi rendering.** The only Marathi text in the whole export is the toggle label **मराठी**. No screen is shown in Marathi.
**DECIDED:** see §2.2.

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

### 2.2 Marathi typography (DECIDED: Noto Sans Devanagari)

**All Marathi text uses Noto Sans Devanagari**: headings, body, labels, buttons, badges, the language toggle label and numbers
inside Marathi sentences. It is one family covering the whole range of weights (400, 500, 600, 700), so Marathi never falls back to a
random system font.

* **Loading:** `next/font/google` with the `devanagari` and `latin` subsets (code in §7). Set `lang="mr"` on `<html>` (or on the
  element) whenever the interface is Marathi, so the browser picks the right shaping and hyphenation.
* **Stacks:** when the UI is Marathi, both the display and the body stack start with Noto Sans Devanagari, then the Latin font as a
  fallback. Monospace code strings (`intent_router`, model names, `0 ms`) stay monospace Latin. They are identifiers, not copy.
* **Line height:** Devanagari has tall ascenders and matras above and below the line, so the tight Latin values clip. Use at least
  **1.6 for body and 1.35 for headings** (the Latin scale uses 1.4 to 1.5 and 1.1 to 1.15).
* **Size:** Devanagari looks smaller than Latin at the same size. Start with body at 17 px (Latin 16) and captions at 14 px, and
  confirm with a Marathi reader on a real phone. *(Approximate: this is a starting point, not a measured value.)*
* **No letter-spacing and no uppercase:** Devanagari has no capital letters, and tracking breaks conjunct letters. In Marathi, drop
  `uppercase` and `tracking-*` from the eyebrow labels ("POSSIBLE CONDITION"): render them as ordinary text at the same weight and
  size.
* **Weight:** use 600 to 700 for headings and 500 for labels. Do not use weights lighter than 400 for Marathi.
* **Length:** Marathi strings are often longer than the English ones. Never fix widths on buttons, badges or chips; let them wrap or
  grow, and test the longest strings on a 360 px screen.
* **Still open:** whether numbers inside Marathi text use Devanagari digits (०१२३) or Western digits (0123). Dates, weights, money and
  confidence values are the cases to check. Ask the Marathi reviewer and apply one rule everywhere.

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
| Filter chip | Pill, 1.5 px `control-border` outline, ink text. **Selected:** filled `ink`, white text, optional count ("Pending review · 3"). |
| Quick-reply chip | Pill with 2 px `brand` outline. **Selected:** filled `brand`, white text. |
| Disabled | Fill `#D4D0C1`, muted text (the empty "Check my crop" button). |
| Loading | Fill `brand-loading`, spinner + "Signing in…". Inputs become `sunken`. |
| Link | `brand`, underlined ("Forgot password?"). |
| Header sign-out | Outline pill, `brand` border. |

### Inputs

* Text input / select / date: `field` white, 1 to 1.5 px **`control-border`** `#7F7B6B` border (at least 3:1), radius 14, height 48.
* Textarea has a right-aligned counter ("22 / 2000"). Date input is the native control with a calendar icon.
* Error: border `#A3261B`, helper text in red below. Disabled: `sunken` fill.
* Locked field (crop = Soybean): `sunken` fill, same shape as an input, with the helper "KrishiMitra covers soybean in
  Maharashtra for now."
* Label above the field, 15 px / 600. Optional or required is a pill at the section heading, not on the field.
* **Focus:** ring and border colour as in §1.8. Placeholder text `#6B6F66` (5.13 : 1 on white).
* **Not shown:** hover state, placeholder text colour for disabled, password show/hide, select dropdown open state.

### Segmented controls

* **Tabs** (Sign in | Create account): `sunken` track, active tab is `surface` with the soft shadow.
* **Language toggle** (English | मराठी): 2 px `control-border` outline pill, active side filled `ink` with white text.
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

Written for Tailwind v3 syntax (it works in v4 through `@config`, or translate to `@theme`). Hex values are the **sampled** ones
above, plus the **DECIDED** values from §1.4, §1.7 and §1.8. The Latin display and body fonts are placeholders until the real font
names are confirmed. Marathi uses Noto Sans Devanagari. Fonts are set from `next/font` CSS variables.

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
        line: {
          DEFAULT: "#D9D6C8", // card hairline (decorative)
          strong: "#A9A594", // DECORATIVE ONLY: dashed empty-state borders, empty step circle. Never a control border.
        },
        "control-border": "#7F7B6B", // DECIDED: every input/select/textarea/chip/toggle border (>= 3:1)
        placeholder: "#6B6F66", // 5.13:1 on white
        ink: { DEFAULT: "#17231B", muted: "#4A5A4F" },
        brand: {
          DEFAULT: "#1F5B3A",
          soft: "#46775B",
          loading: "#3F7255",
          tint: "#E3EDDF",
          wash: "#F1F6EE",
        },
        // DECIDED: soil brown brand ramp. Brand colour, never a status colour.
        soil: {
          50: "#F4ECE3",
          100: "#EADCCB",
          300: "#BFA07F", // decoration only
          500: "#8A5A33", // the brand soil colour; metrics cost bars
          600: "#744B2A",
          700: "#5E3D22", // text
          900: "#3A2515",
        },
        success: { bg: "#E3EDDF", fg: "#1F5B3A" },
        warning: { bg: "#F7E9CC", fg: "#7A4700", deep: "#5E3700", accent: "#B98A2E", glow: "#E9C46A" },
        danger: { bg: "#F8E1DC", card: "#FBEFED", fg: "#8F2217", solid: "#A3261B" }, // card is approximate
        info: { bg: "#E2EAF5", fg: "#1D4F8C", deep: "#163D6D" },
        // DECIDED: confidence bands, all >= 3:1 against the track and the card. Never colour-only (see 1.4).
        band: { low: "#A3261B", medium: "#8A6212", high: "#1F5B3A", track: "#E4E0D1" },
        // DECIDED: focus ring.
        focus: { DEFAULT: "#1D4F8C", dark: "#E9C46A" }, // dark = for use on ink / dark panels
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"], // approximate: a geometric grotesque (Latin)
        sans: ["var(--font-body)", "system-ui", "sans-serif"], // approximate: Mukta-like (Latin)
        mono: ["var(--font-mono)", "ui-monospace", "monospace"], // approximate: IBM Plex Mono-like
        // DECIDED: all Marathi text. Applied by the :lang(mr) rule below, not used directly in markup.
        devanagari: ["var(--font-devanagari)", "var(--font-body)", "system-ui", "sans-serif"],
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
      outlineColor: { focus: "#1D4F8C", "focus-dark": "#E9C46A" },
      screens: { sm: "640px", md: "768px", lg: "1024px", xl: "1280px" },
    },
  },
  plugins: [],
};
export default config;
```

```css
/* app/globals.css: focus and Marathi (DECIDED) */
@layer base {
  /* Visible keyboard focus on everything interactive. Never `outline: none` without this. */
  :where(a, button, input, select, textarea, summary, [role="button"], [role="tab"], [tabindex]):focus-visible {
    outline: 3px solid theme("colors.focus.DEFAULT");
    outline-offset: 2px;
  }
  :where(input, select, textarea):focus-visible {
    border-color: theme("colors.focus.DEFAULT");
  }
  .on-dark :where(a, button, input, select, textarea, [role="button"], [tabindex]):focus-visible {
    outline-color: theme("colors.focus.dark"); /* the dark safety note and any dark panel */
  }

  /* Marathi: Noto Sans Devanagari for everything, looser line height, no tracking, no uppercase. */
  :lang(mr) {
    --font-display: var(--font-devanagari);
    --font-body: var(--font-devanagari);
    line-height: 1.6;
  }
  :lang(mr) :where(h1, h2, h3, h4) { line-height: 1.35; }
  :lang(mr) .tracking-eyebrow,
  :lang(mr) .uppercase { letter-spacing: 0; text-transform: none; }
  :lang(mr) :where(code, pre, .font-mono) { font-family: var(--font-mono), ui-monospace, monospace; }
}
```

```ts
// app/layout.tsx (Latin fonts: replace with the confirmed families; Marathi font is decided)
import { Mukta, IBM_Plex_Mono, Bricolage_Grotesque, Noto_Sans_Devanagari } from "next/font/google";

const display = Bricolage_Grotesque({ subsets: ["latin"], variable: "--font-display" });
const body = Mukta({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-body" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });
const devanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari", "latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-devanagari",
});

// <html lang={locale} className={`${display.variable} ${body.variable} ${mono.variable} ${devanagari.variable}`}>
// where locale is "en" or "mr"; lang="mr" is what switches the :lang(mr) rules above on.
```

---

## 8. Open items for the designer

Resolved (see the **DECIDED** sections above):

* ~~Low and High confidence-band colours~~ (§1.4)
* ~~Soil-brown brand colour~~ (§1.7)
* ~~Darker input border~~ and ~~darker Medium bar~~, both at least 3:1 (§1.6)
* ~~Focus states~~ (§1.8)
* ~~Devanagari font for Marathi~~ (§2.2)

Still open:

1. The real names of the **Latin** display and body fonts (the families in §2 are approximate guesses).
2. **Hover and pressed** states, and dark mode (none shown). Focus is now defined.
3. Tablet and phone layouts for expert and metrics; desktop layout for the farmer app.
4. Shimmer or animation spec for skeletons, spinners and step transitions.
5. **Marathi numerals:** Devanagari or Western digits (§2.2).
6. A Marathi reader's review of the Marathi type sizes and line heights on a real phone (§2.2).
7. Sign-off on where soil brown is used (§1.7), since it is new and does not appear in any screenshot.
