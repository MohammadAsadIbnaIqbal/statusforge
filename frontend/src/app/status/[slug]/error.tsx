"use client";

import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm border border-gray-200 p-8 text-center space-y-4">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <AlertTriangle className="h-6 w-6 text-red-600" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-gray-900">Status Unavailable</h2>
          <p className="mt-2 text-sm text-gray-500">
            We are unable to load the status page at this time. This may be due to a temporary service disruption.
          </p>
        </div>
        <div className="mt-6">
          <Button onClick={() => reset()} className="w-full">
            Try Again
          </Button>
        </div>
      </div>
    </div>
  );
}
