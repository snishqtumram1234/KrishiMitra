import { NextResponse, type NextRequest } from "next/server";
import { HOME, LOGIN_PATH, safeNext } from "@/lib/auth/routing";
import { readSession } from "@/lib/auth/session";
import { isSupabaseConfigured } from "@/lib/env";
import { createServerSupabase } from "@/lib/supabase/server";

/** The link in the confirmation email lands here with a one-time `code`; trade it for a session, then go home. */
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const go = (to: string) => new NextResponse(null, { status: 307, headers: { Location: to, "Cache-Control": "private, no-store" } });
  const code = searchParams.get("code");
  const fail = () => go(`${LOGIN_PATH}?error=confirmLink`);

  if (!code || !isSupabaseConfigured()) return fail();
  const supabase = await createServerSupabase();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) return fail();

  const session = await readSession(supabase);
  if (!session) return fail();
  const target = safeNext(searchParams.get("next"), session.role) ?? HOME[session.role];
  return go(target);
}
