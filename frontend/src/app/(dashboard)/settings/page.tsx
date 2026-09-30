"use client";

import React from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";

export default function PlaceholderPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Coming Soon</h1>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Not Implemented Yet</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500">This feature will be implemented in a later stage.</p>
        </CardContent>
      </Card>
    </div>
  );
}
