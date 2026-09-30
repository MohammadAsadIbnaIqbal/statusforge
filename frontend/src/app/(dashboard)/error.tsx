'use client';

import React, { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);

  return (
    <div className="flex h-[50vh] w-full items-center justify-center">
      <div className="flex max-w-md flex-col items-center space-y-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
          <AlertTriangle className="h-6 w-6 text-red-600" aria-hidden="true" />
        </div>
        <div>
          <h2 className="text-lg font-medium text-gray-900">Something went wrong</h2>
          <p className="mt-2 text-sm text-gray-500">
            We encountered an unexpected error loading this page.
          </p>
        </div>
        <Button onClick={() => reset()}>Try Again</Button>
      </div>
    </div>
  );
}
