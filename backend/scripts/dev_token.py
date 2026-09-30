"""Mint a local test JWT for curl testing WITHOUT a Supabase project (dev only).

Signs with SUPABASE_JWT_SECRET from backend/.env. Refuses to run when ENVIRONMENT=production.
With a real Supabase project, get a token from Supabase Auth instead.

  python scripts/dev_token.py                     # farmer, new random user id
  python scripts/dev_token.py <user-uuid>         # farmer, fixed id
  python scripts/dev_token.py --expert [<uuid>]   # expert (app_metadata.role = "expert")
"""

import sys
import time
import uuid
from pathlib import Path

import jwt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import get_settings  # noqa: E402

s = get_settings()
if s.environment == "production":
    raise SystemExit("Refusing to mint dev tokens in production.")
if not s.supabase_jwt_secret:
    raise SystemExit("Set SUPABASE_JWT_SECRET in backend/.env (any long random string for local dev).")

args = sys.argv[1:]
expert = "--expert" in args
args = [a for a in args if a != "--expert"]
sub = args[0] if args else str(uuid.uuid4())
claims = {"sub": sub, "aud": "authenticated", "role": "authenticated", "exp": int(time.time()) + 3600}
if expert:
    claims["app_metadata"] = {"role": "expert"}
print(jwt.encode(claims, s.supabase_jwt_secret, algorithm="HS256"))
