"""Serves the in-memory (dev/test) store's own short-lived image links.

This route is NOT behind the JWT: the signed, expiring token in the URL is the credential, exactly like a
Supabase Storage signed URL. With the Supabase store, signed URLs point at Supabase Storage and this route
returns 404.
"""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import get_store
from app.services.case_store import CaseStore

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/{token}")
def serve_signed_file(token: str, store: CaseStore = Depends(get_store)):
    lookup = getattr(store, "image_for_signed_token", None)
    image = lookup(token) if lookup else None
    if image is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link is invalid or has expired")
    return Response(
        content=image.data,
        media_type=image.meta.content_type,
        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline",
                 "X-Content-Type-Options": "nosniff"},
    )
