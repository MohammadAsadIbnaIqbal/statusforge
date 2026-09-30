"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useServices } from "@/lib/hooks";
import { apiFetch } from "@/lib/api";

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'destructive'> = {
  OPERATIONAL: 'success',
  DEGRADED_PERFORMANCE: 'warning',
  PARTIAL_OUTAGE: 'warning',
  MAJOR_OUTAGE: 'destructive',
  UNDER_MAINTENANCE: 'default',
};

export default function ServicesPage() {
  const { services, loading, error, refetch } = useServices();
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<number | null>(null);

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this service?")) return;
    
    setIsDeleting(id);
    setDeleteError(null);
    try {
      const token = localStorage.getItem('access_token') || undefined;
      await apiFetch(`/services/${id}`, { method: 'DELETE' }, token);
      await refetch();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDeleteError(err.message);
      } else {
        setDeleteError("Failed to delete service.");
      }
    } finally {
      setIsDeleting(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Services</h1>
          <p className="mt-1 text-sm text-gray-500">Manage the services displayed on your status page.</p>
        </div>
        <Link href="/services/new">
          <Button className="whitespace-nowrap">
            <Plus className="mr-2 h-4 w-4" />
            Add Service
          </Button>
        </Link>
      </div>

      {error && <Alert variant="destructive">{error}</Alert>}
      {deleteError && <Alert variant="destructive">{deleteError}</Alert>}

      <Card>
        <CardContent className="p-0">
          {services.length === 0 ? (
            <div className="p-6">
              <EmptyState
                icon={Plus}
                title="No services found"
                description="Get started by creating your first service."
                action={
                  <Link href="/services/new">
                    <Button variant="outline" className="mt-4">Add Service</Button>
                  </Link>
                }
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Visibility</TableHead>
                  <TableHead>Order</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {services.map((service) => (
                  <TableRow key={service.id}>
                    <TableCell>
                      <div className="font-medium text-gray-900">{service.name}</div>
                      {service.description && (
                        <div className="text-sm text-gray-500 truncate max-w-xs">{service.description}</div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusColors[service.current_status] || 'default'}>
                        {service.current_status.replace(/_/g, ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {service.is_visible ? (
                        <Badge variant="success">Visible</Badge>
                      ) : (
                        <Badge variant="default">Hidden</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-gray-500">
                      {service.display_order}
                    </TableCell>
                    <TableCell className="text-right space-x-2">
                      <Link href={`/services/${service.id}/edit`}>
                        <Button variant="ghost" size="sm" aria-label="Edit">
                          <Pencil className="h-4 w-4 text-gray-500" />
                        </Button>
                      </Link>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        aria-label="Delete"
                        onClick={() => handleDelete(service.id)}
                        isLoading={isDeleting === service.id}
                        disabled={isDeleting !== null}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
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
