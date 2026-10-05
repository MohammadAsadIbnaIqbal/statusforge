import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiFetch, ApiFetchError } from "@/lib/api";

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    status,
    ok: status >= 200 && status < 300,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("apiFetch", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the Firebase ID token as a Bearer header", async () => {
    const fn = mockFetch(200, { ok: true });
    await apiFetch("/services", {}, "id-token-123");
    const [url, init] = fn.mock.calls[0];
    expect(String(url).endsWith("/services")).toBe(true);
    expect(init.headers["Authorization"]).toBe("Bearer id-token-123");
  });

  it("sends the active organization id header only when provided", async () => {
    const fn = mockFetch(200, []);
    await apiFetch("/services", {}, "t", 42);
    expect(fn.mock.calls[0][1].headers["x-organization-id"]).toBe("42");

    await apiFetch("/services", {}, "t");
    expect(fn.mock.calls[1][1].headers["x-organization-id"]).toBeUndefined();
  });

  it("sends no auth headers for public requests", async () => {
    const fn = mockFetch(200, { message: "ok" });
    await apiFetch("/subscribers/confirm/abc");
    const headers = fn.mock.calls[0][1].headers;
    expect(headers["Authorization"]).toBeUndefined();
    expect(headers["x-organization-id"]).toBeUndefined();
  });

  it("returns null for 204 responses", async () => {
    mockFetch(204, null);
    await expect(apiFetch("/services/1", { method: "DELETE" }, "t")).resolves.toBeNull();
  });

  it("throws ApiFetchError carrying status and backend detail on failure", async () => {
    mockFetch(403, { detail: "Invitation email does not match your account" });
    const err = await apiFetch("/invitations/x/accept", { method: "POST" }, "t").catch((e) => e);
    expect(err).toBeInstanceOf(ApiFetchError);
    expect(err.status).toBe(403);
    expect(err.message).toBe("Invitation email does not match your account");
  });

  it("falls back to a generic message when the error has no detail", async () => {
    mockFetch(500, {});
    const err = await apiFetch("/services", {}, "t").catch((e) => e);
    expect(err).toBeInstanceOf(ApiFetchError);
    expect(err.message).toBe("An error occurred");
  });
});
