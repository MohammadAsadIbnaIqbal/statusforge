"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { apiFetch, ApiFetchError } from "@/lib/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";

function describeError(err: unknown, email: string | undefined): string {
  if (err instanceof ApiFetchError) {
    switch (err.status) {
      case 403:
        return (
          "This invitation was sent to a different email address" +
          (email ? " than the one you are signed in with (" + email + ")" : "") +
          ". Sign out and sign in with the invited email."
        );
      case 404:
        return "This invitation link is invalid.";
      case 400:
        // Backend distinguishes expired vs. revoked/already used in the message.
        return err.message;
      case 401:
        return "Your session has expired. Please sign in again.";
    }
    return err.message;
  }
  return "Something went wrong. Please try again later.";
}

export function AcceptInvitation({ token }: { token: string | null }) {
  const { user, token: idToken, loading, logout } = useAuth();
  const [state, setState] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const shell = (children: React.ReactNode) => (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-6 rounded-lg border border-gray-100 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-gray-900">Organization invitation</h1>
        {children}
      </div>
    </div>
  );

  if (!token) {
    return shell(<Alert variant="destructive">This invitation link is missing its token.</Alert>);
  }

  if (loading) {
    return shell(
      <div className="flex justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (!user) {
    const next = encodeURIComponent("/invitations/accept?token=" + encodeURIComponent(token));
    return shell(
      <>
        <p className="text-gray-600">
          Sign in or create an account using the email address this invitation was sent to.
        </p>
        <div className="flex flex-col gap-3">
          <Link
            href={"/login?next=" + next}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
          >
            Sign in
          </Link>
          <Link
            href={"/register?next=" + next}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Create account
          </Link>
        </div>
      </>
    );
  }

  const accept = async () => {
    setState("submitting");
    try {
      await apiFetch(
        "/invitations/" + encodeURIComponent(token) + "/accept",
        { method: "POST" },
        idToken || undefined
      );
      setState("success");
    } catch (err: unknown) {
      setMessage(describeError(err, user.email));
      setState("error");
    }
  };

  if (state === "success") {
    return shell(
      <>
        <Alert variant="success">Invitation accepted. You are now a member of the organization.</Alert>
        <button
          type="button"
          onClick={() => window.location.assign("/dashboard")}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500"
        >
          Go to dashboard
        </button>
      </>
    );
  }

  return shell(
    <>
      <p className="text-gray-600">
        Signed in as <span className="font-medium">{user.email}</span>
      </p>
      {state === "error" && <Alert variant="destructive">{message}</Alert>}
      <div className="flex flex-col gap-3">
        <Button onClick={accept} isLoading={state === "submitting"} disabled={state === "submitting"}>
          Accept invitation
        </Button>
        <button
          type="button"
          onClick={() => logout()}
          className="text-sm font-medium text-blue-600 hover:text-blue-500"
        >
          Sign out
        </button>
      </div>
    </>
  );
}
