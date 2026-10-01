/**
 * Environment access. NEXT_PUBLIC_* values are inlined at build time, so each one must be read with a literal
 * `process.env.NEXT_PUBLIC_X` (a dynamic lookup would be undefined in the browser).
 */
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";
const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const draftBadges = process.env.NEXT_PUBLIC_SHOW_DRAFT_BADGES;

/** Sign-in needs both values. Without them the login page says so instead of failing on submit. */
export function isSupabaseConfigured(): boolean {
  return /^https?:\/\//.test(supabaseUrl) && supabaseKey.length > 0;
}

export function supabaseConfig(): { url: string; key: string } {
  if (!isSupabaseConfigured()) {
    throw new Error("Supabase is not configured: set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY (see .env.local.example).");
  }
  return { url: supabaseUrl, key: supabaseKey };
}

export function apiBaseUrl(): string {
  return apiBase || "http://127.0.0.1:8000";
}

export function draftBadgeFlag(): string | undefined {
  return draftBadges;
}

export const MIN_PASSWORD_LENGTH = 6; // Supabase's default minimum; the design says "At least 6 characters"
