import type { SupabaseClient } from "@supabase/supabase-js";
import type { Role } from "../api-types";
import { roleFromClaims } from "./roles";

export type SessionInfo = { userId: string; email: string | null; role: Role };

/**
 * The signed-in user, or null. Uses getClaims(), which verifies the token's signature (and refreshes an expired
 * token), instead of trusting whatever is in the cookie. The role is read from the same token the backend will
 * receive, so the UI and the API always agree about who the user is.
 *
 * If the auth service cannot be reached the user is treated as signed out; the login page then shows the error.
 */
export async function readSession(supabase: SupabaseClient): Promise<SessionInfo | null> {
  try {
    const { data, error } = await supabase.auth.getClaims();
    const claims = data?.claims;
    if (error || !claims || typeof claims.sub !== "string") return null;
    return {
      userId: claims.sub,
      email: typeof claims.email === "string" ? claims.email : null,
      role: roleFromClaims(claims),
    };
  } catch {
    return null;
  }
}
