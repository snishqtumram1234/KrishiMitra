/**
 * Maps a Supabase Auth failure to one of our own error kinds. The UI shows copy from the dictionary for the kind;
 * Supabase's English error text is never shown.
 */
export type AuthErrorKind =
  | "invalid"
  | "unconfirmed"
  | "rateLimit"
  | "weakPassword"
  | "network"
  | "notConfigured"
  | "confirmLink"
  | "generic";

export const AUTH_ERROR_KINDS: readonly AuthErrorKind[] = [
  "invalid",
  "unconfirmed",
  "rateLimit",
  "weakPassword",
  "network",
  "notConfigured",
  "confirmLink",
  "generic",
];

export function isAuthErrorKind(value: unknown): value is AuthErrorKind {
  return typeof value === "string" && (AUTH_ERROR_KINDS as readonly string[]).includes(value);
}

type ErrorLike = { code?: unknown; name?: unknown; status?: unknown };

export function authErrorKind(error: unknown): AuthErrorKind {
  if (!error || typeof error !== "object") return "generic";
  const { code, name, status } = error as ErrorLike;

  if (name === "AuthRetryableFetchError" || name === "TypeError" || status === 0) return "network";
  switch (code) {
    case "invalid_credentials":
      return "invalid";
    case "email_not_confirmed":
      return "unconfirmed";
    case "over_request_rate_limit":
    case "over_email_send_rate_limit":
    case "over_sms_send_rate_limit":
      return "rateLimit";
    case "weak_password":
      return "weakPassword";
    default:
      break;
  }
  if (status === 429) return "rateLimit";
  return "generic";
}
