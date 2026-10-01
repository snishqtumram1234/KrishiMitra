import "server-only";
import { cache } from "react";
import { redirect } from "next/navigation";
import { isSupabaseConfigured } from "../env";
import { createServerSupabase } from "../supabase/server";
import { FORBIDDEN_PATH, HOME, LOGIN_PATH } from "./routing";
import { readSession, type SessionInfo } from "./session";
import type { Role } from "../api-types";

/** The signed-in user for this request (null when signed out or Supabase is not configured). One check per request. */
export const getSession = cache(async (): Promise<SessionInfo | null> => {
  if (!isSupabaseConfigured()) return null;
  return readSession(await createServerSupabase());
});

/**
 * Layout-level guard, a second line behind the proxy. Signed out goes to sign-in. The wrong role goes where the proxy
 * would have sent them: experts to their queue, everyone else to the 403 page.
 */
export async function requireRole(role: Role): Promise<SessionInfo> {
  const session = await getSession();
  if (!session) redirect(LOGIN_PATH);
  if (session.role !== role) redirect(role === "expert" ? FORBIDDEN_PATH : HOME[session.role]);
  return session;
}
