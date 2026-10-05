import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { TokenAction } from "@/components/TokenAction";

function mockFetch(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      status,
      ok: status >= 200 && status < 300,
      json: async () => body,
    })
  );
}

const props = {
  endpoint: "/subscribers/confirm/tok",
  title: "Confirm subscription",
  loadingText: "Confirming...",
  fallbackSuccess: "Done",
};

describe("TokenAction", () => {
  beforeEach(() => vi.unstubAllGlobals());
  afterEach(() => vi.unstubAllGlobals());

  it("shows the backend success message", async () => {
    mockFetch(200, { message: "Subscription confirmed!" });
    render(<TokenAction {...props} />);
    expect(screen.getByText("Confirming...")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Subscription confirmed!")).toBeInTheDocument());
  });

  it("shows an invalid-link error for a 404", async () => {
    mockFetch(404, { detail: "Invalid confirmation link" });
    render(<TokenAction {...props} />);
    await waitFor(() => expect(screen.getByText("Invalid confirmation link")).toBeInTheDocument());
  });

  it("shows the expired message for a 410", async () => {
    mockFetch(410, { detail: "Confirmation link has expired. Please subscribe again." });
    render(<TokenAction {...props} />);
    await waitFor(() =>
      expect(screen.getByText(/has expired/)).toBeInTheDocument()
    );
  });

  it("calls the backend exactly once", async () => {
    mockFetch(200, { message: "ok" });
    render(<TokenAction {...props} />);
    await waitFor(() => expect(screen.getByText("ok")).toBeInTheDocument());
    expect((globalThis.fetch as unknown as { mock: { calls: unknown[] } }).mock.calls).toHaveLength(1);
  });
});
