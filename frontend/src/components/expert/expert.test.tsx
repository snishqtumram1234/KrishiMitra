// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { I18nProvider } from "@/i18n/client";
import { ReviewForm } from "./ReviewForm";

const api = { reviewExpertCase: vi.fn() };
vi.mock("@/lib/api-client", () => ({
  ApiError: class ApiError extends Error {
    constructor(readonly code: string) {
      super(code);
    }
  },
  getApiClient: () => api,
}));

const view = (onSent = vi.fn(), locale: "en" | "mr" = "en") =>
  render(<I18nProvider locale={locale}><ReviewForm caseId="c1" onSent={onSent} /></I18nProvider>);

beforeEach(() => {
  api.reviewExpertCase.mockReset();
});

describe("ReviewForm", () => {
  it("blocks an empty submit, lists what to fix, and sends nothing", () => {
    view();
    fireEvent.click(screen.getByRole("button", { name: "Save review" }));
    expect(screen.getAllByText("Choose a decision.").length).toBeGreaterThan(0);
    expect(api.reviewExpertCase).not.toHaveBeenCalled();
  });

  it("the category is only available for Likely condition, which then requires one", () => {
    view();
    const select = screen.getByLabelText("Category");
    expect(select).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/Likely condition/));
    expect(select).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Save review" }));
    expect(screen.getAllByText("Choose a category for Likely condition.").length).toBeGreaterThan(0);
    expect(api.reviewExpertCase).not.toHaveBeenCalled();
  });

  it("request_more needs notes, has its own button, and sends only the allowed fields", async () => {
    api.reviewExpertCase.mockResolvedValue({ id: "r" });
    const onSent = vi.fn();
    view(onSent);
    fireEvent.click(screen.getByLabelText(/Ask the farmer for more/));
    expect(screen.getByText("Case moves to Awaiting farmer.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Send request to farmer" }));
    expect(screen.getAllByText("Say what the farmer should send.").length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Notes to the farmer"), { target: { value: "Which leaves are affected?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send request to farmer" }));
    await waitFor(() => expect(onSent).toHaveBeenCalled());
    expect(api.reviewExpertCase).toHaveBeenCalledWith("c1", { decision: "request_more", notes: "Which leaves are affected?" });
  });

  it("always shows the warning that notes are unfiltered and must not contain doses", () => {
    view();
    expect(screen.getByText(/never include pesticide names or doses/)).toBeInTheDocument();
  });

  it("explains a 409 and offers a reload", async () => {
    const { ApiError } = await import("@/lib/api-client");
    api.reviewExpertCase.mockImplementation(() => Promise.reject(new ApiError("conflict" as never, 409, null)));
    view();
    fireEvent.click(screen.getByLabelText(/Not enough evidence/));
    fireEvent.click(screen.getByRole("button", { name: "Save review" }));
    await screen.findByText(/already reviewed/);
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
  });

  it("renders in Marathi with no raw keys", () => {
    const { container } = view(vi.fn(), "mr");
    expect(container.textContent).not.toMatch(/\b(ex|expert)\.[A-Za-z_.]+/);
    expect(screen.getByText("तुमचे पुनरावलोकन")).toBeInTheDocument();
  });
});
