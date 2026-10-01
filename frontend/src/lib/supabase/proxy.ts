import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { readSession, type SessionInfo } from "../auth/session";
import { supabaseConfig } from "../env";
import { SUPABASE_CLIENT_OPTIONS } from "./options";

/**
 * Refresh the Supabase session for this request and read who the user is. Any cookies Supabase wants to set (a
 * refreshed token) are written to both the request (so the page sees them) and the response (so the browser keeps them).
 */
export async function updateSession(
  request: NextRequest,
): Promise<{ response: NextResponse; session: SessionInfo | null }> {
  let response = NextResponse.next({ request });
  const { url, key } = supabaseConfig();
  const supabase = createServerClient(url, key, {
    ...SUPABASE_CLIENT_OPTIONS,
    cookies: {
      getAll: () => request.cookies.getAll(),
      setAll(cookiesToSet) {
        for (const { name, value } of cookiesToSet) request.cookies.set(name, value);
        response = NextResponse.next({ request });
        for (const { name, value, options } of cookiesToSet) response.cookies.set(name, value, options);
      },
    },
  });
  const session = await readSession(supabase);
  return { response, session };
}

/** Carry the refreshed-session cookies over to a redirect or rewrite response. */
export function copyCookies(from: NextResponse, to: NextResponse): NextResponse {
  for (const cookie of from.cookies.getAll()) to.cookies.set(cookie);
  return to;
}
