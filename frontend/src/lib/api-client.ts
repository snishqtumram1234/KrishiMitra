/**
 * THE ONLY MODULE THAT TALKS TO THE KRISHIMITRA BACKEND.
 *
 * Every backend call in the app goes through this file (ESLint forbids `fetch` anywhere else). It adds the Supabase
 * access token, builds URLs, turns every failure into an `ApiError` with a stable `code` the i18n layer can translate,
 * and has one typed function per endpoint in API.md. No pages call it yet; screens added later import `getApiClient()`.
 *
 * It never produces user-facing text: components turn `ApiError.code` into English or Marathi (see i18n/copy.ts).
 */
import type {
  CaseAnalysisOut,
  CaseCreate,
  CaseOut,
  CostLatencyOut,
  ExpertCaseDetail,
  ExpertCaseSummary,
  ExpertReviewRecord,
  ExpertStatus,
  ImageKind,
  ImageOut,
  Overview,
  QuestionCreate,
  ReviewIn,
  RoutesOut,
  RunTrace,
  SignedUrlOut,
  WeatherResult,
} from "./api-types";
import { apiBaseUrl } from "./env";
import { createBrowserSupabase } from "./supabase/browser";

// ---------------------------------------------------------------- endpoint registry (kept in sync with API.md by a test)
export const ENDPOINTS = {
  health: ["GET", "/health"],
  createCase: ["POST", "/api/cases"],
  listCases: ["GET", "/api/cases"],
  getCase: ["GET", "/api/cases/{case_id}"],
  uploadImage: ["POST", "/api/cases/{case_id}/images"],
  imageSignedUrl: ["GET", "/api/cases/{case_id}/images/{image_id}/signed-url"],
  analyzeCase: ["POST", "/api/cases/{case_id}/analyze"],
  followUp: ["POST", "/api/cases/{case_id}/follow-up"],
  latestAnalysis: ["GET", "/api/cases/{case_id}/analysis"],
  askQuestion: ["POST", "/api/questions"],
  getRun: ["GET", "/api/runs/{routing_run_id}"],
  getWeather: ["GET", "/api/weather"],
  listExpertCases: ["GET", "/api/expert/cases"],
  getExpertCase: ["GET", "/api/expert/cases/{case_id}"],
  reviewExpertCase: ["POST", "/api/expert/cases/{case_id}/review"],
  metricsOverview: ["GET", "/api/metrics/overview"],
  metricsRoutes: ["GET", "/api/metrics/routes"],
  metricsCostLatency: ["GET", "/api/metrics/cost-latency"],
} as const;
export type EndpointName = keyof typeof ENDPOINTS;

// ---------------------------------------------------------------- errors
export type ApiErrorCode =
  | "network" // the request never got an answer
  | "timeout"
  | "aborted" // the caller cancelled it
  | "unauthorized" // 401, or no token to send
  | "forbidden" // 403
  | "not_found" // 404
  | "conflict" // 409
  | "payload_too_large" // 413
  | "unsupported_media" // 415
  | "invalid" // 400 / 422
  | "unavailable" // 503
  | "server" // other 5xx, or an unreadable success body
  | "unknown";

export type ValidationIssue = { field: string; message: string; type?: string };

export class ApiError extends Error {
  readonly code: ApiErrorCode;
  readonly status: number | null;
  /** FastAPI's `detail`: a string, a list of validation issues, or an object (unknown district). */
  readonly detail: unknown;
  /** Normalised validation issues for a 422, empty otherwise. */
  readonly issues: ValidationIssue[];
  /** Valid district names, when the API rejected one (422 from GET /api/weather). */
  readonly districts: string[];

  constructor(code: ApiErrorCode, status: number | null, detail: unknown, message?: string) {
    super(message ?? describeDetail(detail) ?? code);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.detail = detail;
    this.issues = issuesFrom(detail);
    this.districts = districtsFrom(detail);
  }
}

export function codeForStatus(status: number): ApiErrorCode {
  if (status === 401) return "unauthorized";
  if (status === 403) return "forbidden";
  if (status === 404) return "not_found";
  if (status === 409) return "conflict";
  if (status === 413) return "payload_too_large";
  if (status === 415) return "unsupported_media";
  if (status === 400 || status === 422) return "invalid";
  if (status === 503) return "unavailable";
  if (status >= 500) return "server";
  return "unknown";
}

function describeDetail(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (d && typeof d === "object" && "msg" in d ? String(d.msg) : "")).filter(Boolean).join("; ") || null;
  if (detail && typeof detail === "object" && "message" in detail) return String((detail as { message: unknown }).message);
  return null;
}

function issuesFrom(detail: unknown): ValidationIssue[] {
  if (!Array.isArray(detail)) return [];
  return detail.flatMap((d): ValidationIssue[] => {
    if (!d || typeof d !== "object") return [];
    const loc = Array.isArray((d as { loc?: unknown }).loc) ? ((d as { loc: unknown[] }).loc) : [];
    const field = loc.filter((p, i) => !(i === 0 && ["body", "query", "path", "form", "header"].includes(String(p)))).join(".");
    return [{ field, message: String((d as { msg?: unknown }).msg ?? ""), type: (d as { type?: string }).type }];
  });
}

function districtsFrom(detail: unknown): string[] {
  if (detail && typeof detail === "object" && !Array.isArray(detail) && "districts" in detail) {
    const d = (detail as { districts: unknown }).districts;
    return Array.isArray(d) ? d.map(String) : [];
  }
  return [];
}

// ---------------------------------------------------------------- URL building
export function buildUrl(
  baseUrl: string,
  template: string,
  pathParams: Record<string, string> = {},
  query: Record<string, string | number | undefined | null> = {},
): string {
  const path = template.replace(/\{([a-z_]+)\}/g, (_m, name: string) => {
    const value = pathParams[name];
    if (value === undefined) throw new Error(`Missing path parameter ${name} for ${template}`);
    return encodeURIComponent(value);
  });
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null) params.set(k, String(v));
  const qs = params.toString();
  return `${baseUrl.replace(/\/+$/, "")}${path}${qs ? `?${qs}` : ""}`;
}

// ---------------------------------------------------------------- the client
export type ApiClientOptions = {
  baseUrl: string;
  /** The Supabase access token to send as `Authorization: Bearer`, or null when signed out. */
  getAccessToken: () => Promise<string | null>;
  /** Called when the API says 401, or when there is no token for an endpoint that needs one. Must be idempotent. */
  onUnauthorized?: () => void;
  fetch?: typeof fetch;
  timeoutMs?: number;
};

type Req = {
  endpoint: EndpointName;
  pathParams?: Record<string, string>;
  query?: Record<string, string | number | undefined | null>;
  json?: unknown;
  form?: FormData;
  timeoutMs?: number;
  signal?: AbortSignal;
};

const SLOW_MS = 60_000; // analysis endpoints run the whole orchestrator (and may wait on a weather call)

export function createApiClient(options: ApiClientOptions) {
  const doFetch = options.fetch ?? ((...a: Parameters<typeof fetch>) => fetch(...a));
  const defaultTimeout = options.timeoutMs ?? 30_000;

  async function request<T>(req: Req): Promise<T> {
    const [method, template] = ENDPOINTS[req.endpoint];
    const needsAuth = req.endpoint !== "health";

    const headers: Record<string, string> = { Accept: "application/json" };
    if (needsAuth) {
      const token = await options.getAccessToken();
      if (!token) {
        options.onUnauthorized?.();
        throw new ApiError("unauthorized", 401, null, "Not signed in");
      }
      headers.Authorization = `Bearer ${token}`;
    }
    let body: BodyInit | undefined;
    if (req.form) {
      body = req.form; // the browser sets the multipart Content-Type and boundary itself
    } else if (req.json !== undefined) {
      body = JSON.stringify(req.json);
      headers["Content-Type"] = "application/json";
    }

    const controller = new AbortController();
    const timeoutMs = req.timeoutMs ?? defaultTimeout;
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    const onExternalAbort = () => controller.abort();
    req.signal?.addEventListener("abort", onExternalAbort);

    let response: Response;
    try {
      response = await doFetch(buildUrl(options.baseUrl, template, req.pathParams, req.query), {
        method,
        headers,
        body,
        signal: controller.signal,
      });
    } catch (err) {
      if (timedOut) throw new ApiError("timeout", null, null, `Timed out after ${timeoutMs} ms`);
      if (req.signal?.aborted) throw new ApiError("aborted", null, null, "Request was cancelled");
      throw new ApiError("network", null, null, err instanceof Error ? err.message : "Network error");
    } finally {
      clearTimeout(timer);
      req.signal?.removeEventListener("abort", onExternalAbort);
    }

    let payload: unknown = null;
    const text = await response.text().catch(() => "");
    if (text) {
      try {
        payload = JSON.parse(text);
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as { detail: unknown }).detail : null;
      const code = codeForStatus(response.status);
      if (code === "unauthorized") options.onUnauthorized?.();
      throw new ApiError(code, response.status, detail);
    }
    if (payload === null) throw new ApiError("server", response.status, null, "The API returned an unreadable response");
    return payload as T;
  }

  return {
    health: () => request<{ status: string; app: string; environment: string }>({ endpoint: "health" }),

    // cases
    createCase: (body: CaseCreate) => request<CaseOut>({ endpoint: "createCase", json: body }),
    listCases: () => request<CaseOut[]>({ endpoint: "listCases" }),
    getCase: (caseId: string) => request<CaseOut>({ endpoint: "getCase", pathParams: { case_id: caseId } }),
    uploadImage: (caseId: string, input: { kind: ImageKind; file: Blob }) => {
      const form = new FormData();
      form.set("kind", input.kind);
      form.set("file", input.file);
      return request<ImageOut>({ endpoint: "uploadImage", pathParams: { case_id: caseId }, form });
    },
    imageSignedUrl: (caseId: string, imageId: string) =>
      request<SignedUrlOut>({ endpoint: "imageSignedUrl", pathParams: { case_id: caseId, image_id: imageId } }),

    // analysis
    analyzeCase: (caseId: string, signal?: AbortSignal) =>
      request<CaseAnalysisOut>({ endpoint: "analyzeCase", pathParams: { case_id: caseId }, timeoutMs: SLOW_MS, signal }),
    followUp: (
      caseId: string,
      input: { answer?: string; questionId?: string; option?: string; kind?: ImageKind; file?: Blob },
      signal?: AbortSignal,
    ) => {
      const form = new FormData();
      if (input.answer) form.set("answer", input.answer);
      if (input.questionId) form.set("question_id", input.questionId);
      if (input.option) form.set("option", input.option);
      if (input.kind) form.set("kind", input.kind);
      if (input.file) form.set("file", input.file);
      return request<CaseAnalysisOut>({
        endpoint: "followUp",
        pathParams: { case_id: caseId },
        form,
        timeoutMs: SLOW_MS,
        signal,
      });
    },
    latestAnalysis: (caseId: string) =>
      request<CaseAnalysisOut>({ endpoint: "latestAnalysis", pathParams: { case_id: caseId } }),
    askQuestion: (body: QuestionCreate, signal?: AbortSignal) =>
      request<CaseAnalysisOut>({ endpoint: "askQuestion", json: body, timeoutMs: SLOW_MS, signal }),
    getRun: (routingRunId: string) =>
      request<RunTrace>({ endpoint: "getRun", pathParams: { routing_run_id: routingRunId } }),

    // weather
    getWeather: (district?: string) => request<WeatherResult>({ endpoint: "getWeather", query: { district } }),

    // expert (role: expert)
    listExpertCases: (status?: ExpertStatus | "all") =>
      request<ExpertCaseSummary[]>({ endpoint: "listExpertCases", query: { status } }),
    getExpertCase: (caseId: string) =>
      request<ExpertCaseDetail>({ endpoint: "getExpertCase", pathParams: { case_id: caseId } }),
    reviewExpertCase: (caseId: string, body: ReviewIn) =>
      request<ExpertReviewRecord>({ endpoint: "reviewExpertCase", pathParams: { case_id: caseId }, json: body }),

    // metrics (role: expert); days = 7 | 30 | 90, omit for all time
    metricsOverview: (days?: number) => request<Overview>({ endpoint: "metricsOverview", query: { days } }),
    metricsRoutes: (days?: number) => request<RoutesOut>({ endpoint: "metricsRoutes", query: { days } }),
    metricsCostLatency: (days?: number) =>
      request<CostLatencyOut>({ endpoint: "metricsCostLatency", query: { days } }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

// ---------------------------------------------------------------- the default (browser) client
let browserClient: ApiClient | null = null;

/**
 * The shared client for code running in the browser. It reads the API address from NEXT_PUBLIC_API_BASE_URL and the
 * token from the Supabase session. On a 401 it signs the user out locally and sends them to the login page.
 * (Server-side code creates its own with createApiClient and the token it already has.)
 */
export function getApiClient(): ApiClient {
  if (browserClient) return browserClient;
  const supabase = createBrowserSupabase();
  browserClient = createApiClient({
    baseUrl: apiBaseUrl(),
    getAccessToken: async () => (await supabase.auth.getSession()).data.session?.access_token ?? null,
    onUnauthorized: () => {
      void supabase.auth.signOut({ scope: "local" }).finally(() => {
        // full page load on purpose: drops every in-memory cache of the expired session
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        if (typeof window !== "undefined") window.location.assign("/login?reason=session_expired");
      });
    },
  });
  return browserClient;
}
