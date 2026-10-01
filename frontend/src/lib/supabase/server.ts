import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { supabaseConfig } from "../env";
import { SUPABASE_CLIENT_OPTIONS } from "./options";

/** Supabase client for Server Components, Route Handlers and Server Actions (reads and writes the session cookies). */
export async function createServerSupabase() {
  const { url, key } = supabaseConfig();
  const store = await cookies();
  return createServerClient(url, key, {
    ...SUPABASE_CLIENT_OPTIONS,
    cookies: {
      getAll: () => store.getAll(),
      setAll(cookiesToSet) {
        try {
          for (const { name, value, options } of cookiesToSet) store.set(name, value, options);
        } catch {
          // Called from a Server Component, which cannot set cookies. The proxy refreshes the session instead.
        }
      },
    },
  });
}
