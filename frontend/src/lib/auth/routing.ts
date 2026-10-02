/**
 * Who may open which page, as one pure function. The proxy calls it for every request, and the layouts re-check
 * (defence in depth). The backend still enforces roles on its own; this only decides what the UI shows.
 *
 *   signed out  -> /login (with ?next= for protected pages)
 *   farmer      -> /dashboard; farmer pages only. Expert pages answer 403.
 *   expert      -> /expert;    expert pages only. Farmer pages redirect to the expert home.
 */
import type { Role } from "../api-types";

export type SessionLike = { role: Role } | null;

export const HOME: Record<Role, string> = { farmer: "/dashboard", expert: "/expert" };
/** Path prefixes of each role's area. Add a prefix here when a new screen is built. */
export const FARMER_AREAS = ["/dashboard", "/checks"] as const;
export const EXPERT_AREAS = ["/expert", "/metrics"] as const;
export const LOGIN_PATH = "/login";
export const FORBIDDEN_PATH = "/403";

export type Access =
  | { kind: "next" }
  | { kind: "redirect"; to: string }
  | { kind: "forbidden"; area: "expert" };

export function normalizePath(pathname: string): string {
  return pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
}

export function inArea(pathname: string, prefixes: readonly string[]): boolean {
  const p = normalizePath(pathname);
  return prefixes.some((prefix) => p === prefix || p.startsWith(`${prefix}/`));
}

export function roleOfArea(pathname: string): Role | null {
  if (inArea(pathname, FARMER_AREAS)) return "farmer";
  if (inArea(pathname, EXPERT_AREAS)) return "expert";
  return null;
}

/**
 * A `?next=` value is only followed if it is a plain same-site path (no scheme, no `//host`, no backslash) that this
 * role may open. Anything else is ignored, so the login page can never be used as an open redirect.
 */
export function safeNext(next: string | null | undefined, role: Role): string | null {
  if (!next || next[0] !== "/" || next.startsWith("//") || next.includes("\\") || /[\u0000-\u001f]/.test(next)) {
    return null;
  }
  let url: URL;
  try {
    url = new URL(next, "http://placeholder.invalid");
  } catch {
    return null;
  }
  if (url.origin !== "http://placeholder.invalid") return null;
  const area = roleOfArea(url.pathname);
  if (area !== null && area !== role) return null;
  if (url.pathname === LOGIN_PATH || url.pathname === "/signup" || url.pathname.startsWith("/auth/")) return null;
  return `${url.pathname}${url.search}`;
}

export function loginRedirect(pathname: string, search = ""): string {
  const target = `${normalizePath(pathname)}${search}`;
  return target === "/" ? LOGIN_PATH : `${LOGIN_PATH}?next=${encodeURIComponent(target)}`;
}

export function decideAccess(input: { pathname: string; search?: string; session: SessionLike }): Access {
  const { session } = input;
  const pathname = normalizePath(input.pathname);
  const search = input.search ?? "";

  if (pathname === "/auth" || pathname.startsWith("/auth/")) return { kind: "next" };

  if (pathname === LOGIN_PATH || pathname === "/signup") {
    if (!session) return { kind: "next" };
    const next = safeNext(new URLSearchParams(search).get("next"), session.role);
    return { kind: "redirect", to: next ?? HOME[session.role] };
  }

  // "/" is the public landing page: everyone can see it, signed in or not
  if (pathname === "/") return { kind: "next" };

  if (pathname === FORBIDDEN_PATH) {
    return session ? { kind: "next" } : { kind: "redirect", to: LOGIN_PATH };
  }

  const area = roleOfArea(pathname);
  if (area === null) return { kind: "next" };
  if (!session) return { kind: "redirect", to: loginRedirect(pathname, search) };
  if (area === "expert") return session.role === "expert" ? { kind: "next" } : { kind: "forbidden", area: "expert" };
  return session.role === "farmer" ? { kind: "next" } : { kind: "redirect", to: HOME.expert };
}
