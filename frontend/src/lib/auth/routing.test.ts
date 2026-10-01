import { describe, expect, it } from "vitest";
import { authErrorKind } from "./errors";
import { roleFromClaims } from "./roles";
import { decideAccess, loginRedirect, safeNext } from "./routing";

const farmer = { role: "farmer" as const };
const expert = { role: "expert" as const };

describe("decideAccess", () => {
  it("sends signed-out visitors of protected pages to login, remembering where they were going", () => {
    expect(decideAccess({ pathname: "/dashboard", session: null })).toEqual({
      kind: "redirect",
      to: "/login?next=%2Fdashboard",
    });
    expect(decideAccess({ pathname: "/expert/cases/1", search: "?a=1", session: null })).toEqual({
      kind: "redirect",
      to: "/login?next=%2Fexpert%2Fcases%2F1%3Fa%3D1",
    });
  });
  it("sends each role home from / and from login", () => {
    expect(decideAccess({ pathname: "/", session: farmer })).toEqual({ kind: "redirect", to: "/dashboard" });
    expect(decideAccess({ pathname: "/", session: expert })).toEqual({ kind: "redirect", to: "/expert" });
    expect(decideAccess({ pathname: "/", session: null })).toEqual({ kind: "redirect", to: "/login" });
    expect(decideAccess({ pathname: "/login", session: expert })).toEqual({ kind: "redirect", to: "/expert" });
    expect(decideAccess({ pathname: "/signup", session: farmer })).toEqual({ kind: "redirect", to: "/dashboard" });
  });
  it("follows a safe ?next= after sign-in", () => {
    expect(decideAccess({ pathname: "/login", search: "?next=%2Fdashboard%2Fx", session: farmer })).toEqual({
      kind: "redirect",
      to: "/dashboard/x",
    });
    expect(decideAccess({ pathname: "/login", search: "?next=%2Fexpert", session: farmer })).toEqual({
      kind: "redirect",
      to: "/dashboard",
    });
  });
  it("lets signed-out visitors open login and signup", () => {
    expect(decideAccess({ pathname: "/login", session: null })).toEqual({ kind: "next" });
    expect(decideAccess({ pathname: "/signup", session: null })).toEqual({ kind: "next" });
  });
  it("answers 403 for a farmer on any expert page, including nested and trailing-slash paths", () => {
    for (const pathname of ["/expert", "/expert/", "/expert/cases/9", "/metrics", "/metrics/routes"]) {
      expect(decideAccess({ pathname, session: farmer })).toEqual({ kind: "forbidden", area: "expert" });
    }
  });
  it("does not confuse look-alike paths with expert pages", () => {
    expect(decideAccess({ pathname: "/experts-guide", session: farmer })).toEqual({ kind: "next" });
  });
  it("keeps experts out of farmer pages", () => {
    expect(decideAccess({ pathname: "/dashboard", session: expert })).toEqual({ kind: "redirect", to: "/expert" });
    expect(decideAccess({ pathname: "/expert", session: expert })).toEqual({ kind: "next" });
  });
  it("never intercepts auth routes", () => {
    expect(decideAccess({ pathname: "/auth/callback", session: null })).toEqual({ kind: "next" });
    expect(decideAccess({ pathname: "/auth/signout", session: farmer })).toEqual({ kind: "next" });
  });
  it("only shows /403 to signed-in users", () => {
    expect(decideAccess({ pathname: "/403", session: farmer })).toEqual({ kind: "next" });
    expect(decideAccess({ pathname: "/403", session: null })).toEqual({ kind: "redirect", to: "/login" });
  });
});

describe("safeNext", () => {
  it("accepts same-site paths this role may open", () => {
    expect(safeNext("/dashboard?x=1", "farmer")).toBe("/dashboard?x=1");
    expect(safeNext("/expert/cases/2", "expert")).toBe("/expert/cases/2");
  });
  it.each([
    "https://evil.example",
    "//evil.example",
    "/\\evil.example",
    "javascript:alert(1)",
    "evil",
    "",
    "/a\nb",
    "/login",
    "/auth/callback",
  ])("rejects %j", (value) => expect(safeNext(value, "farmer")).toBeNull());
  it("rejects pages of the other role", () => {
    expect(safeNext("/expert", "farmer")).toBeNull();
    expect(safeNext("/dashboard", "expert")).toBeNull();
  });
  it("loginRedirect from the root has no next", () => {
    expect(loginRedirect("/")).toBe("/login");
  });
});

describe("roleFromClaims", () => {
  it("is expert only for app_metadata.role equal to expert", () => {
    expect(roleFromClaims({ app_metadata: { role: "expert" } })).toBe("expert");
    expect(roleFromClaims({ app_metadata: { role: "Expert" } })).toBe("farmer");
    expect(roleFromClaims({ app_metadata: { role: ["expert"] } })).toBe("farmer");
  });
  it("ignores user_metadata, which the user can edit", () => {
    expect(roleFromClaims({ user_metadata: { role: "expert" } })).toBe("farmer");
    expect(roleFromClaims({ role: "expert" })).toBe("farmer");
  });
  it("defaults to farmer for anything odd", () => {
    for (const v of [null, undefined, "x", 3, {}, { app_metadata: null }]) expect(roleFromClaims(v)).toBe("farmer");
  });
});

describe("authErrorKind", () => {
  it("maps Supabase error codes to our kinds", () => {
    expect(authErrorKind({ code: "invalid_credentials" })).toBe("invalid");
    expect(authErrorKind({ code: "email_not_confirmed" })).toBe("unconfirmed");
    expect(authErrorKind({ code: "over_request_rate_limit" })).toBe("rateLimit");
    expect(authErrorKind({ status: 429 })).toBe("rateLimit");
    expect(authErrorKind({ code: "weak_password" })).toBe("weakPassword");
    expect(authErrorKind({ name: "AuthRetryableFetchError", status: 0 })).toBe("network");
    expect(authErrorKind({ code: "something_new" })).toBe("generic");
    expect(authErrorKind(null)).toBe("generic");
  });
});
