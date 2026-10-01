# KrishiMitra frontend

Next.js (App Router) + TypeScript + Tailwind v4. Built so far: layout, English and Marathi i18n, Supabase Auth
(sign in, create account), role-based redirects, a 403 page, and the single backend client. No mock data: the
dashboard and review-queue pages are placeholders that show only the real session.

## Run

```bash
cp .env.local.example .env.local   # then fill in the Supabase values
npm install
npm run dev                        # http://localhost:3000
```

Needs Node 20.9 or later (Node 22 is recommended; supabase-js has announced it will drop Node 20).

| Command | What it does |
|---|---|
| `npm run check` | typecheck, lint and tests |
| `npm run build` | production build |
| `npm run api:types` | regenerate `src/lib/api-schema.d.ts` from `openapi.snapshot.json` |
| `npm run i18n:review` | prints the Marathi review sheet (every unreviewed string, English beside it) |

### Trying it without a Supabase project

`scripts/fake-auth-server.mjs` is a dev-only stand-in for Supabase Auth with two local accounts
(`farmer@example.test`, `expert@example.test`, password `test-password-1`). It signs ES256 tokens and publishes a JWKS,
so the app verifies them the way it verifies real ones.

```bash
node scripts/fake-auth-server.mjs
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321 NEXT_PUBLIC_SUPABASE_ANON_KEY=local-test-key npm run dev
```

## How it works

**Roles.** The role is `app_metadata.role === "expert"` in the access token (read with `getClaims()`, which verifies the
signature). `user_metadata` is editable by the user and is never read. Everyone else is a farmer. The UI therefore
agrees with what the backend accepts.

**Redirects** (`src/lib/auth/routing.ts`, one pure function, applied by `src/proxy.ts` and re-checked in the layouts):
signed out goes to `/login?next=...`; farmers go to `/dashboard`, experts to `/expert`; a farmer opening an expert page
gets a real HTTP 403 rendering `/403` with the URL unchanged; an expert opening a farmer page is sent to `/expert`.
`?next=` is followed only if it is a same-site path the role may open.

**403 page** (`src/app/(neutral)/403`). Neutral header only (brand, language, sign out). It never renders the expert
shell. "Try again" refreshes the token so a newly granted role takes effect.

**One API client.** Every backend call goes through `src/lib/api-client.ts`; ESLint forbids `fetch` anywhere else. It
attaches the bearer token, maps errors to stable codes (`ApiError.code`), and on a 401 signs out and returns to
`/login?reason=session_expired`. Types come from the backend's OpenAPI (`api-schema.d.ts`); the code lists in
`api-types.ts` have compile-time checks that fail when the backend adds a value.

**i18n** (`src/i18n`). `messages/en.ts` is the source of truth; `messages/mr.ts` must have the same keys (the compiler
checks it) and the same `{placeholders}` (a test checks it). Screens never show the backend's English `message`; they
build text from structured fields with `copy.ts` (`stateCopy`, `reasonCopy`, `bandLabel`, ...). Adding a decision
state, reason code or band to the API without adding its strings fails `tsc`.

**Marathi is a draft.** Every Marathi string needs native review. A "Marathi draft: needs native review" banner shows
while the UI is Marathi (hide it with `NEXT_PUBLIC_SHOW_DRAFT_BADGES=false`). When a reviewer signs off on a string, add
its key to `REVIEWED_KEYS` in `src/i18n/review.ts` in the same commit as their corrections. Digits in Marathi text are
Latin (0-9) until the open decision in `design-handoff/README.md` is made; one constant in `format.ts` switches it.

## Known gaps

- Forgot-password is not built (the design shows the link, but no screens exist for it).
- The login error shows a banner only, not the extra "This password doesn't match" line from the design.
- `/dashboard` and `/expert` are placeholders. `/metrics` is guarded as an expert area but has no page yet.
- Latin fonts (Space Grotesk, Mukta, IBM Plex Mono) are stand-ins until the designer confirms the real ones.
