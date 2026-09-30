"use client";

import React from "react";
import { Users } from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useSubscribers } from "@/lib/hooks";

export default function SubscribersPage() {
  const { subscribers, loading, error } = useSubscribers();

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Subscribers</h1>
          <p className="mt-1 text-sm text-gray-500">Manage users subscribed to your status updates.</p>
        </div>
      </div>

      {error && <Alert variant="destructive">{error}</Alert>}

      <Card>
        <CardContent className="p-0">
          {subscribers.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={Users}
                title="No subscribers yet"
                description="When users subscribe to your status page, they will appear here."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Subscribed On</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subscribers.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell>
                      <div className="font-medium text-gray-900">{sub.email}</div>
                    </TableCell>
                    <TableCell>
                      {sub.is_confirmed ? (
                        <Badge variant="success">Confirmed</Badge>
                      ) : (
                        <Badge variant="warning">Unconfirmed</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-gray-500 text-sm whitespace-nowrap">
                      {new Date(sub.created_at).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
