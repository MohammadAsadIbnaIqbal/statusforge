"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { apiFetch, ApiFetchError } from "@/lib/api";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Alert } from "@/components/ui/Alert";

interface TokenActionProps {
  /** Backend endpoint (including the token) that performs the action. */
  endpoint: string;
  title: string;
  loadingText: string;
  fallbackSuccess: string;
}

/**
 * Public page body that performs a single backend token action on load
 * (subscriber confirmation / unsubscribe). Requires no authentication.
 */
export function TokenAction({ endpoint, title, loadingText, fallbackSuccess }: TokenActionProps) {
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");
  const started = useRef(false);

  useEffect(() => {
    // Tokens are single-use; guard against duplicate effect runs.
    if (started.current) return;
    started.current = true;

    apiFetch(endpoint)
      .then((data) => {
        setMessage((data && data.message) || fallbackSuccess);
        setState("success");
      })
      .catch((err: unknown) => {
        setMessage(
          err instanceof ApiFetchError
            ? err.message
            : "Something went wrong. Please try again later."
        );
        setState("error");
      });
  }, [endpoint, fallbackSuccess]);

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-md space-y-6 rounded-lg border border-gray-100 bg-white p-8 text-center shadow-sm">
        <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
        {state === "loading" && (
          <div className="flex flex-col items-center gap-3 text-gray-600">
            <LoadingSpinner />
            <p>{loadingText}</p>
          </div>
        )}
        {state === "success" && <Alert variant="success">{message}</Alert>}
        {state === "error" && <Alert variant="destructive">{message}</Alert>}
        <Link href="/" className="text-sm font-medium text-blue-600 hover:text-blue-500">
          Back to StatusForge
        </Link>
      </div>
    </div>
  );
}
