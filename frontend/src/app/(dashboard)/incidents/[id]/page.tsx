"use client";

import React, { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Clock } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { Incident } from "@/types/api";
import { useApi } from "@/lib/useApi";

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


export default function IncidentDetailPage() {
  const { fetchApi } = useApi();
  const params = useParams();
  const id = params.id as string;


  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [updateMessage, setUpdateMessage] = useState("");
  const [updateStatus, setUpdateStatus] = useState("INVESTIGATING");
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState("");

  const fetchIncident = async () => {
    try {
      const data = await fetchApi(`/incidents/${id}`, {});
      setIncident(data);
      if (data && data.status !== 'RESOLVED') {
        setUpdateStatus(data.status); // Default to current status
      }
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError("Failed to load incident.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => fetchIncident(), 0);
    return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setUpdateError("");
    setUpdating(true);

    try {
      await fetchApi(`/incidents/${id}/updates`, {
        method: "POST",
        body: JSON.stringify({
          status: updateStatus,
          message: updateMessage
        }),
      });

      setUpdateMessage("");
      await fetchIncident(); // Refresh incident data
    } catch (err: unknown) {
      if (err instanceof Error) setUpdateError(err.message);
      else setUpdateError("Failed to update incident.");
    } finally {
      setUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-gray-400" />
      </div>
    );
  }

  if (error || !incident) {
    return <Alert variant="destructive">{error || "Incident not found"}</Alert>;
  }

  const isResolved = incident.status === 'RESOLVED';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className="flex items-center space-x-4 flex-1">
          <Link href="/incidents">
            <Button variant="outline" size="sm" className="h-8 w-8 p-0 shrink-0">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <h1 className="text-2xl font-semibold text-gray-900 truncate">{incident.title}</h1>
        </div>
        <div className="flex items-center flex-wrap gap-2">
          <Badge variant={statusColors[incident.status] || 'default'} className="text-sm px-3 py-1">
            {incident.status}
          </Badge>
          <Badge variant={impactColors[incident.impact] || 'default'} className="text-sm px-3 py-1">
            {incident.impact} IMPACT
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-8">
                {incident.updates && incident.updates.length > 0 ? (
                  <div className="relative border-l border-gray-200 ml-3 space-y-8">
                    {incident.updates.slice().reverse().map((update) => (
                      <div key={update.id} className="relative pl-6">
                        <span className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full bg-gray-200 ring-4 ring-white" />
                        <div className="flex items-center space-x-2 text-sm text-gray-500 mb-1">
                          <span className="font-medium text-gray-900">{update.status}</span>
                          <span>•</span>
                          <time dateTime={update.created_at} className="flex items-center">
                            <Clock className="h-3 w-3 mr-1" />
                            {new Date(update.created_at).toLocaleString()}
                          </time>
                        </div>
                        <div className="mt-2 text-gray-700 whitespace-pre-wrap">
                          {update.message}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">No updates yet.</p>
                )}
              </div>
            </CardContent>
          </Card>

          {!isResolved && (
            <Card>
              <CardHeader>
                <CardTitle>Post Update</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleUpdate} className="space-y-4">
                  {updateError && <Alert variant="destructive">{updateError}</Alert>}

                  <div className="flex flex-col space-y-1.5">
                    <label htmlFor="status" className="text-sm font-medium text-gray-700">New Status</label>
                    <select
                      id="status"
                      className="h-10 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:border-gray-400 focus-visible:ring-1 focus-visible:ring-gray-900"
                      value={updateStatus}
                      onChange={(e) => setUpdateStatus(e.target.value)}
                    >
                      <option value="INVESTIGATING">Investigating</option>
                      <option value="IDENTIFIED">Identified</option>
                      <option value="MONITORING">Monitoring</option>
                      <option value="RESOLVED">Resolved</option>
                    </select>
                  </div>

                  <div className="flex flex-col space-y-1.5">
                    <label htmlFor="message" className="text-sm font-medium text-gray-700">Update Message</label>
                    <textarea
                      id="message"
                      required
                      className="min-h-[100px] rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:border-gray-400 focus-visible:ring-1 focus-visible:ring-gray-900"
                      value={updateMessage}
                      onChange={(e) => setUpdateMessage(e.target.value)}
                      placeholder="Share an update on the situation..."
                    />
                  </div>

                  <div className="flex justify-end pt-2">
                    <Button type="submit" isLoading={updating}>
                      Post Update
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div>
                <span className="block text-gray-500 mb-1">Created</span>
                <span className="text-gray-900">{new Date(incident.created_at).toLocaleString()}</span>
              </div>
              {incident.resolved_at && (
                <div>
                  <span className="block text-gray-500 mb-1">Resolved</span>
                  <span className="text-gray-900">{new Date(incident.resolved_at).toLocaleString()}</span>
                </div>
              )}
              <div>
                <span className="block text-gray-500 mb-2">Affected Services</span>
                <div className="flex flex-wrap gap-2">
                  {incident.services.map(s => (
                    <Badge key={s.id} variant="outline">{s.name}</Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
