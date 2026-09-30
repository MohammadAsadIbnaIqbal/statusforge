import React from 'react';
import { Loader2 } from 'lucide-react';

export default function DashboardLoading() {
  return (
    <div className="flex h-[50vh] w-full items-center justify-center">
      <div className="flex flex-col items-center space-y-4 text-gray-500">
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="text-sm font-medium">Loading dashboard...</p>
      </div>
    </div>
  );
}
