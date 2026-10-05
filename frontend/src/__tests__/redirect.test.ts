import { describe, it, expect } from "vitest";
import { safeNextPath } from "@/lib/redirect";

describe("safeNextPath", () => {
  it("defaults to the dashboard when missing", () => {
    expect(safeNextPath(null)).toBe("/dashboard");
    expect(safeNextPath(undefined)).toBe("/dashboard");
    expect(safeNextPath("")).toBe("/dashboard");
  });

  it("accepts same-origin paths including query strings", () => {
    expect(safeNextPath("/invitations/accept?token=abc")).toBe("/invitations/accept?token=abc");
  });

  it("rejects off-site and protocol-relative redirects", () => {
    expect(safeNextPath("https://evil.example.com")).toBe("/dashboard");
    expect(safeNextPath("//evil.example.com")).toBe("/dashboard");
    expect(safeNextPath("/\\evil.example.com")).toBe("/dashboard");
    expect(safeNextPath("javascript:alert(1)")).toBe("/dashboard");
  });
});
