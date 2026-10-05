"use client";

import React from "react";
import Link from "next/link";
import { Activity, Server, AlertTriangle, Users } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { useServices, useIncidents, useSubscribers } from "@/lib/hooks";

export default function DashboardPage() {
  const { user } = useAuth();

  const { services, loading: sLoading } = useServices();
  const { incidents, loading: iLoading } = useIncidents();
  const { subscribers, loading: subLoading } = useSubscribers();

  if (sLoading || iLoading || subLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-gray-400" />
      </div>
    );
  }

  const nonOperationalCount = services.filter(s => s.current_status !== 'OPERATIONAL').length;

  const allIncidents = incidents?.items || [];
  const activeIncidents = allIncidents.filter(i => i.status !== 'RESOLVED');
  const recentIncidents = allIncidents.slice(0, 5);

  const confirmedSubscribers = subscribers.filter(s => s.is_confirmed).length;

  let overallStatus = "All Systems Operational";
  let statusColor = "text-green-600";
  let statusBg = "bg-green-100";

  if (activeIncidents.length > 0) {
    const hasCritical = activeIncidents.some(i => i.impact === 'CRITICAL');
    const hasMajor = activeIncidents.some(i => i.impact === 'MAJOR');
    if (hasCritical) {
      overallStatus = "Critical Outage";
      statusColor = "text-red-600";
      statusBg = "bg-red-100";
    } else if (hasMajor) {
      overallStatus = "Major Outage";
      statusColor = "text-red-600";
      statusBg = "bg-red-100";
    } else {
      overallStatus = "Minor Service Issues";
      statusColor = "text-yellow-600";
      statusBg = "bg-yellow-100";
    }
  } else if (nonOperationalCount > 0) {
    overallStatus = "Degraded Performance";
    statusColor = "text-yellow-600";
    statusBg = "bg-yellow-100";
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Welcome back, {user?.email}. Here&apos;s an overview of your status page.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="shadow-sm border-gray-200">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl shrink-0 ${statusBg} ${statusColor}`}>
                <Activity className="h-6 w-6" />
              </div>
              <div className="ml-4 min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-500 truncate">Overall Status</p>
                <p className={`text-2xl font-semibold leading-none truncate ${statusColor}`} title={overallStatus}>{overallStatus}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-gray-200">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 text-blue-600 shrink-0">
                <Server className="h-6 w-6" />
              </div>
              <div className="ml-4 min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-500 truncate">Services</p>
                <p className="text-2xl font-semibold text-gray-900 leading-none">{services.length}</p>
              </div>
            </div>
            {nonOperationalCount > 0 && (
              <div className="ml-16 mt-1">
                <span className="text-xs font-medium text-red-600">{nonOperationalCount} degraded</span>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-sm border-gray-200">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-yellow-100 text-yellow-600 shrink-0">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div className="ml-4 min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-500 truncate">Active Incidents</p>
                <p className="text-2xl font-semibold text-gray-900 leading-none">{activeIncidents.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-sm border-gray-200">
          <CardContent className="p-6">
            <div className="flex items-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-purple-100 text-purple-600 shrink-0">
                <Users className="h-6 w-6" />
              </div>
              <div className="ml-4 min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-500 truncate">Subscribers</p>
                <p className="text-2xl font-semibold text-gray-900 leading-none">{subscribers.length}</p>
              </div>
            </div>
            <div className="ml-16 mt-1">
              <span className="text-xs font-medium text-gray-500">{confirmedSubscribers} confirmed</span>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between w-full">
            <CardTitle>Recent Incidents</CardTitle>
              <Link href="/incidents">
                <Button variant="ghost" size="sm">View All</Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {recentIncidents.length === 0 ? (
              <p className="text-sm text-gray-500 py-4 text-center">No recent incidents.</p>
            ) : (
              <div className="space-y-4">
                {recentIncidents.map(incident => (
                  <div key={incident.id} className="flex items-center justify-between border-b border-gray-100 last:border-0 pb-4 last:pb-0">
                    <div>
                      <Link href={`/incidents/${incident.id}`} className="font-medium text-gray-900 hover:underline">
                        {incident.title}
                      </Link>
                      <p className="text-sm text-gray-500">
                        {new Date(incident.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Badge variant={incident.status === 'RESOLVED' ? 'success' : 'warning'}>
                      {incident.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Link href="/incidents/new" className="block">
                <Button className="w-full justify-start" variant="outline">
                  <AlertTriangle className="mr-2 h-4 w-4 text-gray-500" />
                  Report New Incident
                </Button>
              </Link>
              <Link href="/services/new" className="block">
                <Button className="w-full justify-start" variant="outline">
                  <Server className="mr-2 h-4 w-4 text-gray-500" />
                  Add Service
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
