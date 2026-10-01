import { createBrowserClient } from "@supabase/ssr";
import { supabaseConfig } from "../env";
import { SUPABASE_CLIENT_OPTIONS } from "./options";

/** Supabase client for code running in the browser. Keeps the session in cookies, so the server sees it too. */
export function createBrowserSupabase() {
  const { url, key } = supabaseConfig();
  return createBrowserClient(url, key, SUPABASE_CLIENT_OPTIONS);
}
