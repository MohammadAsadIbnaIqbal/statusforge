"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { useServices } from "@/lib/hooks";
import { useApi } from "@/lib/useApi";

export default function NewIncidentPage() {
  const { fetchApi } = useApi();
  const router = useRouter();
  const { services } = useServices();

  const [formData, setFormData] = useState({
    title: "",
    impact: "MINOR",
    message: "",
    service_ids: [] as number[],
  });

  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const toggleService = (id: number) => {
    setFormData(prev => ({
      ...prev,
      service_ids: prev.service_ids.includes(id)
        ? prev.service_ids.filter(sId => sId !== id)
        : [...prev.service_ids, id]
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.service_ids.length === 0) {
      setError("Please select at least one affected service.");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await fetchApi("/incidents", {
        method: "POST",
        body: JSON.stringify(formData),
      });

      router.push("/incidents");
    } catch (err: unknown) {
      if (err instanceof Error) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const errorObj = err as any;
        if (Array.isArray(errorObj.detail)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setError(errorObj.detail.map((d: any) => d.msg).join(", "));
        } else {
          setError(err.message || "Failed to create incident.");
        }
      } else {
        setError("Failed to create incident.");
      }
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Report Incident</h1>
        <Link href="/incidents">
          <Button variant="ghost">Cancel</Button>
        </Link>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && <Alert variant="destructive">{error}</Alert>}

            <div className="space-y-4">
              <Input
                id="title"
                label="Incident Title"
                type="text"
                required
                value={formData.title}
                onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                placeholder="e.g. API Outage"
                maxLength={200}
              />

              <div className="flex flex-col space-y-1.5 w-full">
                <label htmlFor="impact" className="text-sm font-medium leading-none text-gray-700">
                  Impact Level
                </label>
                <select
                  id="impact"
                  className="flex h-10 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:border-gray-400 focus-visible:ring-1 focus-visible:ring-gray-900"
                  value={formData.impact}
                  onChange={(e) => setFormData(prev => ({ ...prev, impact: e.target.value }))}
                >
                  <option value="NONE">None</option>
                  <option value="MINOR">Minor</option>
                  <option value="MAJOR">Major</option>
                  <option value="CRITICAL">Critical</option>
                </select>
              </div>

              <div className="flex flex-col space-y-2 pt-2">
                <label className="text-sm font-medium leading-none text-gray-700">
                  Affected Services
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 rounded-md border border-gray-200">
                  {services.length === 0 ? (
                    <p className="text-sm text-gray-500">No services available. Create a service first.</p>
                  ) : (
                    services.map(service => (
                      <div key={service.id} className="flex items-center space-x-2">
                        <input
                          type="checkbox"
                          id={`service-${service.id}`}
                          checked={formData.service_ids.includes(service.id)}
                          onChange={() => toggleService(service.id)}
                          className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                        />
                        <label htmlFor={`service-${service.id}`} className="text-sm font-medium text-gray-700 cursor-pointer">
                          {service.name}
                        </label>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="flex flex-col space-y-1.5 w-full">
                <label htmlFor="message" className="text-sm font-medium leading-none text-gray-700">
                  Initial Update Message
                </label>
                <textarea
                  id="message"
                  required
                  className="flex min-h-[100px] w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus-visible:outline-none focus-visible:border-gray-400 focus-visible:ring-1 focus-visible:ring-gray-900 transition-colors"
                  value={formData.message}
                  onChange={(e) => setFormData(prev => ({ ...prev, message: e.target.value }))}
                  placeholder="e.g. We are investigating reports of API errors..."
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-4">
              <Link href="/incidents">
                <Button type="button" variant="outline">Cancel</Button>
              </Link>
              <Button type="submit" isLoading={isLoading} disabled={services.length === 0}>
                Report Incident
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
