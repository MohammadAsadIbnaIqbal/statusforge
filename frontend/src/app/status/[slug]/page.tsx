/* eslint-disable @typescript-eslint/no-explicit-any */
import React from "react";
import { notFound } from "next/navigation";
import { Metadata } from "next";
import { CheckCircle2, AlertTriangle, AlertCircle, XCircle, Wrench, Activity } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { PublicStatusResponse, Incident, Service } from "@/types/api";
import { SubscribeForm } from "./SubscribeForm";

const statusConfig: Record<string, any> = {
  OPERATIONAL: { label: "All Systems Operational", color: "text-emerald-500", bg: "bg-emerald-500", icon: CheckCircle2, bannerBg: "bg-emerald-50 border-emerald-200", bannerText: "text-emerald-800" },
  DEGRADED_PERFORMANCE: { label: "Degraded Performance", color: "text-amber-500", bg: "bg-amber-500", icon: AlertTriangle, bannerBg: "bg-amber-50 border-amber-200", bannerText: "text-amber-800" },
  PARTIAL_OUTAGE: { label: "Partial Outage", color: "text-orange-500", bg: "bg-orange-500", icon: AlertCircle, bannerBg: "bg-orange-50 border-orange-200", bannerText: "text-orange-800" },
  MAJOR_OUTAGE: { label: "Major Outage", color: "text-rose-500", bg: "bg-rose-500", icon: XCircle, bannerBg: "bg-rose-50 border-rose-200", bannerText: "text-rose-800" },
  UNDER_MAINTENANCE: { label: "Under Maintenance", color: "text-blue-500", bg: "bg-blue-500", icon: Wrench, bannerBg: "bg-blue-50 border-blue-200", bannerText: "text-blue-800" },
};

const incidentStatusConfig: Record<string, any> = {
  INVESTIGATING: { label: "Investigating", color: "text-rose-600" },
  IDENTIFIED: { label: "Identified", color: "text-amber-600" },
  MONITORING: { label: "Monitoring", color: "text-blue-600" },
  RESOLVED: { label: "Resolved", color: "text-emerald-600" },
};

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const data: PublicStatusResponse = await apiFetch(`/status/${slug}`, { cache: "no-store" });
    return {
      title: `${data.organization.name} Status`,
      description: `Current system status and incident history for ${data.organization.name}`,
    };
  } catch {
    return { title: "Status Page Not Found" };
  }
}

function formatDate(dateStr: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short"
  }).format(new Date(dateStr));
}

function IncidentCard({ incident }: { incident: Incident }) {
  const sortedUpdates = [...incident.updates].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm mb-6">
      <div className="p-5 border-b border-gray-100 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">{incident.title}</h3>
          <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500">
            <span className="font-medium text-gray-900">{incidentStatusConfig[incident.status].label}</span>
            <span>&bull;</span>
            <span className="flex items-center">
              <Activity className="h-3.5 w-3.5 mr-1" />
              {incident.impact} Impact
            </span>
            <span>&bull;</span>
            <span>{incident.services.map(s => s.name).join(", ")}</span>
          </div>
        </div>
      </div>
      <div className="p-5">
        <div className="space-y-6">
          {sortedUpdates.length > 0 ? (
            sortedUpdates.map((update, idx) => (
              <div key={idx} className="relative pl-6">
                <div className="absolute left-0 top-1.5 h-2 w-2 rounded-full bg-gray-300" />
                {idx !== sortedUpdates.length - 1 && (
                  <div className="absolute left-[3px] top-4 bottom-[-24px] w-0.5 bg-gray-100" />
                )}
                <div className="text-sm font-medium text-gray-900 mb-1">
                  <span className={incidentStatusConfig[update.status].color}>{incidentStatusConfig[update.status].label}</span>
                  <span className="text-gray-400 mx-2">&mdash;</span>
                  <span className="text-gray-500 font-normal">{formatDate(update.created_at)}</span>
                </div>
                <div className="text-gray-700 whitespace-pre-wrap text-sm">{update.message}</div>
              </div>
            ))
          ) : (
            <p className="text-sm text-gray-500 italic">No updates available.</p>
          )}
        </div>
      </div>
    </div>
  );
}

export const dynamic = "force-dynamic";

export default async function PublicStatusPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  let data: PublicStatusResponse;
  try {
    data = await apiFetch(`/status/${slug}`, { cache: "no-store" });
  } catch (error: any) /* eslint-disable-line @typescript-eslint/no-explicit-any */ {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    if (error?.status === 404) {
      notFound();
    }
    throw error;
  }

  const config = statusConfig[data.overall_status];
  const Icon = config.icon;

  return (
    <div className="min-h-screen bg-gray-50/50">
      <header className="bg-white border-b border-gray-200 py-6">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-xl font-semibold text-gray-900 flex items-center">
            {data.organization.name} Status
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-12">
        <section>
          <div className={`rounded-xl border p-5 flex items-center ${config.bannerBg}`}>
            <Icon className={`h-8 w-8 mr-4 ${config.color}`} />
            <h2 className={`text-xl font-medium ${config.bannerText}`}>{config.label}</h2>
          </div>
        </section>

        <section>
          <SubscribeForm slug={slug} />
        </section>

        {data.services.length > 0 ? (
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Services</h2>
            <div className="rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm">
              <ul className="divide-y divide-gray-100">
                {data.services.map((service: any) => {
                  const sConf = statusConfig[service.status];
                  return (
                    <li key={service.id} className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div>
                        <div className="font-medium text-gray-900">{service.name}</div>
                        {service.description && (
                          <div className="text-sm text-gray-500 mt-0.5">{service.description}</div>
                        )}
                      </div>
                      <div className="flex items-center text-sm font-medium">
                        <span className={`h-2.5 w-2.5 rounded-full mr-2 ${sConf.bg}`}></span>
                        <span className={sConf.color}>{sConf.label}</span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          </section>
        ) : (
          <section>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Services</h2>
            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-500 shadow-sm">
              No services are currently monitored.
            </div>
          </section>
        )}

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Active Incidents</h2>
          {data.active_incidents.length > 0 ? (
            <div>
              {data.active_incidents.map(inc => (
                <IncidentCard key={inc.id} incident={inc} />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-500 shadow-sm">
              No active incidents.
            </div>
          )}
        </section>

        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Past 7 Days</h2>
          {data.recent_incidents.length > 0 ? (
            <div>
              {data.recent_incidents.map(inc => (
                <IncidentCard key={inc.id} incident={inc} />
              ))}
            </div>
          ) : (
            <div className="py-4 text-gray-500">
              No incidents reported in the past 7 days.
            </div>
          )}
        </section>

      </main>

      <footer className="border-t border-gray-200 bg-white py-8 mt-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-500">
          Powered by StatusForge
        </div>
      </footer>
    </div>
  );
}
