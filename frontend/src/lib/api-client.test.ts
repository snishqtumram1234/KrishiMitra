import { describe, expect, it, vi } from "vitest";
import { ApiError, buildUrl, codeForStatus, createApiClient } from "./api-client";

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function client(fetchImpl: typeof fetch, token: string | null = "tok") {
  const onUnauthorized = vi.fn();
  const api = createApiClient({
    baseUrl: "http://api.test",
    getAccessToken: async () => token,
    onUnauthorized,
    fetch: fetchImpl,
  });
  return { api, onUnauthorized };
}

describe("buildUrl", () => {
  it("encodes path parameters and skips empty query values", () => {
    const url = buildUrl("http://api.test/", "/api/cases/{case_id}", { case_id: "a/b c" }, { limit: 5, x: undefined, y: null });
    expect(url).toBe("http://api.test/api/cases/a%2Fb%20c?limit=5");
  });
});

describe("codeForStatus", () => {
  it("maps statuses to stable codes", () => {
    expect(codeForStatus(401)).toBe("unauthorized");
    expect(codeForStatus(403)).toBe("forbidden");
    expect(codeForStatus(404)).toBe("not_found");
    expect(codeForStatus(422)).toBe("invalid");
    expect(codeForStatus(503)).toBe("unavailable");
    expect(codeForStatus(500)).toBe("server");
  });
});

describe("api client", () => {
  it("sends the bearer token and parses JSON", async () => {
    const fetchMock = vi.fn(async () => json([]));
    const { api } = client(fetchMock as unknown as typeof fetch);
    await api.listCases();
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/api/cases");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });

  it("makes no network call without a token, and reports unauthorized", async () => {
    const fetchMock = vi.fn();
    const { api, onUnauthorized } = client(fetchMock as unknown as typeof fetch, null);
    await expect(api.listCases()).rejects.toMatchObject({ code: "unauthorized", status: 401 });
    expect(fetchMock).not.toHaveBeenCalled();
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("health needs no token", async () => {
    const fetchMock = vi.fn(async () => json({ status: "ok" }));
    const { api } = client(fetchMock as unknown as typeof fetch, null);
    await api.health();
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it("turns a 401 into onUnauthorized plus an ApiError", async () => {
    const { api, onUnauthorized } = client((async () => json({ detail: "bad token" }, 401)) as unknown as typeof fetch);
    await expect(api.listCases()).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledOnce();
  });

  it("exposes validation issues and a network failure code", async () => {
    const issues = [{ loc: ["body", "district"], msg: "bad", type: "value_error" }];
    const { api } = client((async () => json({ detail: issues }, 422)) as unknown as typeof fetch);
    const err = (await api.listCases().catch((e: unknown) => e)) as ApiError;
    expect(err.code).toBe("invalid");
    expect(err.issues).toEqual([{ field: "district", message: "bad", type: "value_error" }]);

    const down = client((async () => {
      throw new TypeError("failed to fetch");
    }) as unknown as typeof fetch);
    await expect(down.api.listCases()).rejects.toMatchObject({ code: "network" });
  });
});
