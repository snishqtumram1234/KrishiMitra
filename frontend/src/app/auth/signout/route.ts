import { NextResponse } from "next/server";
import { LOGIN_PATH } from "@/lib/auth/routing";
import { isSupabaseConfigured } from "@/lib/env";
import { createServerSupabase } from "@/lib/supabase/server";

/** Sign out (POST from a plain form, so it works without JavaScript) and return to the sign-in page. */
export async function POST() {
  if (isSupabaseConfigured()) {
    const supabase = await createServerSupabase();
    await supabase.auth.signOut();
  }
  // A relative Location keeps the browser on the host it used, whatever host the server believes it has.
  return new NextResponse(null, { status: 303, headers: { Location: LOGIN_PATH, "Cache-Control": "private, no-store" } });
}
