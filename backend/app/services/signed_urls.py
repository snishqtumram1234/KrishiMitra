"""Short-lived signed image links for the in-memory (dev/test) store.

token = <image_id>.<expires_epoch>.<hmac_sha256(secret, "<image_id>.<expires_epoch>")>
The /api/files/<token> route verifies the signature and expiry, then serves the bytes. With the Supabase
store, links are signed by Supabase Storage instead and this module is not used.
"""

import hashlib
import hmac
import time
from uuid import UUID

SIGNED_URL_TTL_SECONDS = 300  # 5 minutes


def _sig(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def sign(image_id: UUID, secret: str, ttl: int = SIGNED_URL_TTL_SECONDS, now: float | None = None) -> tuple[str, int]:
    """Return (token, expires_at_epoch)."""
    expires = int((now if now is not None else time.time()) + ttl)
    payload = f"{image_id}.{expires}"
    return f"{payload}.{_sig(secret, payload)}", expires


def verify(token: str, secret: str, now: float | None = None) -> UUID | None:
    """Return the image id if the token is authentic and not expired, else None."""
    try:
        image_id_s, expires_s, sig = token.split(".")
        expires = int(expires_s)
        image_id = UUID(image_id_s)
    except ValueError:
        return None
    if not hmac.compare_digest(sig, _sig(secret, f"{image_id_s}.{expires_s}")):
        return None
    if (now if now is not None else time.time()) >= expires:
        return None
    return image_id
