import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { ApiFetchError } from "@/lib/api";

const authState: {
  user: { email: string } | null;
  token: string | null;
  loading: boolean;
  logout: () => void;
} = { user: null, token: null, loading: false, logout: vi.fn() };

vi.mock("@/lib/auth", () => ({ useAuth: () => authState }));

const apiFetchMock = vi.fn();
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, apiFetch: (...args: unknown[]) => apiFetchMock(...args) };
});

import { AcceptInvitation } from "@/app/invitations/accept/AcceptInvitation";

describe("AcceptInvitation", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    authState.user = null;
    authState.token = null;
    authState.loading = false;
  });

  it("shows an error when the token is missing", () => {
    render(<AcceptInvitation token={null} />);
    expect(screen.getByText(/missing its token/)).toBeInTheDocument();
  });

  it("sends unauthenticated users to login/register preserving the invitation in `next`", () => {
    render(<AcceptInvitation token="raw-token" />);
    const expectedNext = encodeURIComponent("/invitations/accept?token=raw-token");
    expect(screen.getByText("Sign in").closest("a")).toHaveAttribute("href", "/login?next=" + expectedNext);
    expect(screen.getByText("Create account").closest("a")).toHaveAttribute("href", "/register?next=" + expectedNext);
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("does not display the raw token", () => {
    authState.user = { email: "invitee@example.com" };
    authState.token = "id-token";
    const { container } = render(<AcceptInvitation token="super-secret-raw-token" />);
    expect(container.textContent).not.toContain("super-secret-raw-token");
  });

  it("posts to the backend accept endpoint with the Firebase ID token", async () => {
    authState.user = { email: "invitee@example.com" };
    authState.token = "id-token";
    apiFetchMock.mockResolvedValue({ message: "ok" });
    render(<AcceptInvitation token="raw-token" />);
    fireEvent.click(screen.getByText("Accept invitation"));
    await waitFor(() => expect(screen.getByText(/Invitation accepted/)).toBeInTheDocument());
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/invitations/raw-token/accept",
      { method: "POST" },
      "id-token"
    );
  });

  it("explains a wrong-email rejection (403) without granting access", async () => {
    authState.user = { email: "wrong@example.com" };
    authState.token = "id-token";
    apiFetchMock.mockRejectedValue(new ApiFetchError("Invitation email does not match your account", 403));
    render(<AcceptInvitation token="raw-token" />);
    fireEvent.click(screen.getByText("Accept invitation"));
    await waitFor(() => expect(screen.getByText(/different email address/)).toBeInTheDocument());
    expect(screen.queryByText(/Invitation accepted/)).not.toBeInTheDocument();
  });

  it("shows the backend message for expired/revoked/used invitations (400)", async () => {
    authState.user = { email: "invitee@example.com" };
    authState.token = "id-token";
    apiFetchMock.mockRejectedValue(new ApiFetchError("Invitation has expired", 400));
    render(<AcceptInvitation token="raw-token" />);
    fireEvent.click(screen.getByText("Accept invitation"));
    await waitFor(() => expect(screen.getByText("Invitation has expired")).toBeInTheDocument());
  });

  it("shows an invalid-link message for 404", async () => {
    authState.user = { email: "invitee@example.com" };
    authState.token = "id-token";
    apiFetchMock.mockRejectedValue(new ApiFetchError("Invalid invitation token", 404));
    render(<AcceptInvitation token="raw-token" />);
    fireEvent.click(screen.getByText("Accept invitation"));
    await waitFor(() => expect(screen.getByText(/invitation link is invalid/)).toBeInTheDocument());
  });
});
