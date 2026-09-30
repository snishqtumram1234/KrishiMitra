# Demo cases

- `cases.json`: 50 demo questions (English and Marathi) covering every orchestration path:
  image diagnosis, bad photos, weather, treatment safety, expert requests, unsupported requests,
  advisory lookups, unclear questions with follow-ups. Used by `backend/scripts/seed_demo.py`.
- `weather/`: demo weather fallback data (see its README).
- `images/` (optional): drop real leaf photos here and reference them as `"image": {"file": "name.jpg"}`.

**Images are synthetic by default.** With no real photos, the seed script draws leaf-like pictures
(green texture with spots / pustules / holes, or a deliberately blurry / dark / tiny / non-leaf
image). Routing, quality-gate, cost and latency numbers are real; vision *predictions* on synthetic
pictures are meaningless, so do not read accuracy from them.

Each case may carry `expect_path` / `expect_state`; the seed script reports any mismatch.
