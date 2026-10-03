// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/i18n/client";
import { CropCheckForm } from "./CropCheckForm";

const push = vi.fn();
const api = {
  createCase: vi.fn(),
  uploadImage: vi.fn(),
  analyzeCase: vi.fn(),
};

vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn(), refresh: vi.fn() }) }));
vi.mock("@/lib/api-client", () => ({ ApiError: class extends Error {}, getApiClient: () => api }));
// the sheet is a native <dialog>, which jsdom cannot open; its content is not what this test is about
vi.mock("./SubmitSheet", () => ({ SubmitSheet: () => null }));

const JPEG = new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 0, 16, 0x4a, 0x46, 0x49, 0x46, 0]);

beforeEach(() => {
  vi.clearAllMocks();
  api.createCase.mockResolvedValue({ id: "case-1" });
  api.uploadImage.mockResolvedValue({});
  api.analyzeCase.mockResolvedValue({ case_id: "case-1" });
  vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, blob: async () => new Blob([JPEG], { type: "image/jpeg" }) })));
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});

describe("demo picker on the crop-check form", () => {
  it("fills the form from a sample, then submits it like a normal check", async () => {
    render(
      <I18nProvider locale="en">
        <CropCheckForm />
      </I18nProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /Use sample photo: Yellow-brown spots/ }));

    await waitFor(() =>
      expect((screen.getByLabelText(/describe/i, { selector: "textarea" }) as HTMLTextAreaElement).value).toMatch(
        /yellow-brown spots/i,
      ),
    );
    await waitFor(() => expect(push).toHaveBeenCalledWith("/checks/case-1/progress"), { timeout: 5000 });

    const body = api.createCase.mock.calls[0][0];
    expect(body).toMatchObject({ crop: "soybean", district: "Pune", language: "en", growth_stage: "R3" });
    expect(body.symptom_started_at).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    const upload = api.uploadImage.mock.calls[0];
    expect(upload[0]).toBe("case-1");
    expect(upload[1].kind).toBe("leaf_closeup");
    expect(upload[1].file).toBeInstanceOf(File);
    expect(api.analyzeCase.mock.calls[0][0]).toBe("case-1");
  });

  it("offers every sample as a button", () => {
    render(
      <I18nProvider locale="en">
        <CropCheckForm />
      </I18nProvider>,
    );
    expect(screen.getAllByRole("button", { name: /Use sample photo/ })).toHaveLength(4);
  });
});
