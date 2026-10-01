/**
 * DEV/TEST ONLY. A tiny stand-in for Supabase Auth (GoTrue) so the login, signup, redirects and 403 can be tried
 * without a Supabase project. It is NOT used by the app and holds no real accounts: the two users below exist only
 * on localhost while this script runs. Tokens are signed ES256 and published at /auth/v1/.well-known/jwks.json, so the
 * frontend (and the backend in JWKS mode) verify them exactly as they would verify real Supabase tokens.
 *
 *   node scripts/fake-auth-server.mjs            (listens on http://127.0.0.1:54321)
 *   NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321 NEXT_PUBLIC_SUPABASE_ANON_KEY=local-test-key npm run dev
 *
 * Test accounts: farmer@example.test and expert@example.test, both with the password "test-password-1".
 * POST /__admin/role {email, role} changes a user's role claim (to test "just got expert access, try again").
 */
import { createServer } from "node:http";
import { createHash, generateKeyPairSync, randomUUID, sign } from "node:crypto";

const PORT = Number(process.env.FAKE_AUTH_PORT ?? 54321);
const ISSUER = `http://127.0.0.1:${PORT}/auth/v1`;
const { publicKey, privateKey } = generateKeyPairSync("ec", { namedCurve: "P-256" });
const jwk = { ...publicKey.export({ format: "jwk" }), kid: "fake-key-1", alg: "ES256", use: "sig" };

const users = new Map();
function addUser(email, password, role, confirmed = true) {
  users.set(email, { id: randomUUID(), email, password, role, confirmed });
}
addUser("farmer@example.test", "test-password-1", "farmer");
addUser("expert@example.test", "test-password-1", "expert");

const b64 = (v) => Buffer.from(typeof v === "string" ? v : JSON.stringify(v)).toString("base64url");
function accessToken(user, ttl = 3600) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "ES256", typ: "JWT", kid: jwk.kid };
  const payload = {
    iss: ISSUER,
    aud: "authenticated",
    sub: user.id,
    email: user.email,
    role: "authenticated",
    iat: now,
    exp: now + ttl,
    session_id: randomUUID(),
    app_metadata: { provider: "email", ...(user.role === "expert" ? { role: "expert" } : {}) },
    user_metadata: {},
  };
  const input = `${b64(header)}.${b64(payload)}`;
  const sig = sign("sha256", Buffer.from(input), { key: privateKey, dsaEncoding: "ieee-p1363" }).toString("base64url");
  return { token: `${input}.${sig}`, expiresAt: payload.exp, ttl };
}

const refreshTokens = new Map();
function sessionFor(user) {
  const { token, expiresAt, ttl } = accessToken(user);
  const refresh = createHash("sha256").update(randomUUID()).digest("hex").slice(0, 12);
  refreshTokens.set(refresh, user.email);
  return {
    access_token: token,
    token_type: "bearer",
    expires_in: ttl,
    expires_at: expiresAt,
    refresh_token: refresh,
    user: userJson(user),
  };
}
const userJson = (u) => ({
  id: u.id,
  aud: "authenticated",
  role: "authenticated",
  email: u.email,
  email_confirmed_at: u.confirmed ? new Date().toISOString() : null,
  app_metadata: { provider: "email", ...(u.role === "expert" ? { role: "expert" } : {}) },
  user_metadata: {},
  created_at: new Date().toISOString(),
});

function send(res, status, body) {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Methods": "*",
  });
  res.end(body === undefined ? "" : JSON.stringify(body));
}
const err = (res, status, code, msg) => send(res, status, { code: status, error_code: code, msg });

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  try {
    return JSON.parse(Buffer.concat(chunks).toString() || "{}");
  } catch {
    return {};
  }
}

createServer(async (req, res) => {
  const url = new URL(req.url, ISSUER);
  const path = url.pathname;
  if (req.method === "OPTIONS") return send(res, 204);

  if (path === "/auth/v1/.well-known/jwks.json") return send(res, 200, { keys: [jwk] });

  if (path === "/auth/v1/token" && req.method === "POST") {
    const body = await readBody(req);
    const grant = url.searchParams.get("grant_type");
    if (grant === "password") {
      const user = users.get(String(body.email ?? "").toLowerCase());
      if (!user || user.password !== body.password) return err(res, 400, "invalid_credentials", "Invalid login credentials");
      if (!user.confirmed) return err(res, 400, "email_not_confirmed", "Email not confirmed");
      return send(res, 200, sessionFor(user));
    }
    if (grant === "refresh_token") {
      const email = refreshTokens.get(body.refresh_token);
      const user = email && users.get(email);
      if (!user) return err(res, 400, "refresh_token_not_found", "Invalid Refresh Token");
      refreshTokens.delete(body.refresh_token);
      return send(res, 200, sessionFor(user));
    }
    return err(res, 400, "unsupported_grant_type", "unsupported");
  }

  if (path === "/auth/v1/signup" && req.method === "POST") {
    const body = await readBody(req);
    const email = String(body.email ?? "").toLowerCase();
    if (String(body.password ?? "").length < 6) return err(res, 422, "weak_password", "Password should be at least 6 characters.");
    // like Supabase with email confirmation on: a new user gets no session until the link is opened
    if (!users.has(email)) addUser(email, body.password, "farmer", false);
    return send(res, 200, userJson(users.get(email)));
  }

  if (path === "/auth/v1/user" && req.method === "GET") {
    // tokens are verified through the JWKS above, so this endpoint is never needed
    return err(res, 401, "bad_jwt", "use JWKS");
  }

  if (path === "/auth/v1/logout") return send(res, 204);

  if (path === "/__admin/role" && req.method === "POST") {
    const body = await readBody(req);
    const user = users.get(String(body.email ?? "").toLowerCase());
    if (!user) return err(res, 404, "not_found", "no such user");
    user.role = body.role === "expert" ? "expert" : "farmer";
    return send(res, 200, { email: user.email, role: user.role });
  }

  err(res, 404, "not_found", `no route for ${req.method} ${path}`);
}).listen(PORT, "127.0.0.1", () => console.log(`fake Supabase Auth on ${ISSUER}`));
