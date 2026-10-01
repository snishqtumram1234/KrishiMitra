import type { Role } from "../api-types";

/**
 * The app role from a token's claims. Only `app_metadata.role === "expert"` makes an expert (exact match); it can
 * only be set server-side. `user_metadata` is editable by the user and is NEVER read. Everyone else is a farmer.
 */
export function roleFromClaims(claims: unknown): Role {
  if (!claims || typeof claims !== "object") return "farmer";
  const appMetadata = (claims as { app_metadata?: unknown }).app_metadata;
  if (appMetadata && typeof appMetadata === "object" && (appMetadata as { role?: unknown }).role === "expert") {
    return "expert";
  }
  return "farmer";
}
