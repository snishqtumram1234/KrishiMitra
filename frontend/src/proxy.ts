import { NextResponse, type NextRequest } from "next/server";
import { decideAccess, FORBIDDEN_PATH, type Access, type SessionLike } from "./lib/auth/routing";
import { isSupabaseConfigured } from "./lib/env";
import { copyCookies, updateSession } from "./lib/supabase/proxy";

/**
 * Runs before every page request: keeps the Supabase session fresh and applies the role-based redirects from
 * lib/auth/routing.ts. This is an optimistic check for the UI. Pages re-check, and the backend enforces roles itself.
 */
export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  let response = NextResponse.next({ request });
  let session: SessionLike = null;
  if (isSupabaseConfigured()) ({ response, session } = await updateSession(request));

  const access: Access = decideAccess({ pathname, search, session });
  if (access.kind === "next") return response;

  const out =
    access.kind === "redirect"
      ? NextResponse.redirect(new URL(access.to, request.url))
      : // a real 403 status, with the URL left as the user typed it, rendered by the neutral /403 page
        NextResponse.rewrite(new URL(`${FORBIDDEN_PATH}?area=${access.area}`, request.url), { status: 403 });
  out.headers.set("Cache-Control", "private, no-store");
  return copyCookies(response, out);
}

export const config = {
  // Skip Next internals and any file with an extension (images, fonts, icons).
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.[a-zA-Z0-9]+$).*)"],
};
