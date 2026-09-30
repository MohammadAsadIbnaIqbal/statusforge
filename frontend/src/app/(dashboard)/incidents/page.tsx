"use client";

import React from "react";
import Link from "next/link";
import { Plus, Eye } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useIncidents } from "@/lib/hooks";

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'destructive'> = {
  INVESTIGATING: 'destructive',
  IDENTIFIED: 'warning',
  MONITORING: 'warning',
  RESOLVED: 'success',
};

const impactColors: Record<string, 'default' | 'success' | 'warning' | 'destructive'> = {
  NONE: 'default',
  MINOR: 'warning',
  MAJOR: 'warning',
  CRITICAL: 'destructive',
};

export default function IncidentsPage() {
  const { incidents, loading, error } = useIncidents();

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-gray-400" />
      </div>
    );
  }

  const items = incidents?.items || [];
  
  // Active incidents first, then resolved
  const activeIncidents = items.filter(i => i.status !== 'RESOLVED');
  const resolvedIncidents = items.filter(i => i.status === 'RESOLVED');
  const sortedIncidents = [...activeIncidents, ...resolvedIncidents];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Incidents</h1>
          <p className="mt-1 text-sm text-gray-500">Track and manage service disruptions.</p>
        </div>
        <Link href="/incidents/new">
          <Button className="whitespace-nowrap">
            <Plus className="mr-2 h-4 w-4" />
            Report Incident
          </Button>
        </Link>
      </div>

      {error && <Alert variant="destructive">{error}</Alert>}

      <Card>
        <CardContent className="p-0">
          {sortedIncidents.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={Plus}
                title="No incidents reported"
                description="Your services are running smoothly. Report an incident if there are issues."
                action={
                  <Link href="/incidents/new">
                    <Button variant="outline" className="mt-4">Report Incident</Button>
                  </Link>
                }
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Impact</TableHead>
                  <TableHead>Affected Services</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">View</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedIncidents.map((incident) => (
                  <TableRow key={incident.id}>
                    <TableCell>
                      <div className="font-medium text-gray-900">{incident.title}</div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusColors[incident.status] || 'default'}>
                        {incident.status}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={impactColors[incident.impact] || 'default'}>
                        {incident.impact}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {incident.services.map(s => (
                          <span key={s.id} className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600">
                            {s.name}
                          </span>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-gray-500 text-sm whitespace-nowrap">
                      {new Date(incident.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Link href={`/incidents/${incident.id}`}>
                        <Button variant="ghost" size="sm" aria-label="View Details">
                          <Eye className="h-4 w-4 text-gray-500" />
                        </Button>
                      </Link>
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
