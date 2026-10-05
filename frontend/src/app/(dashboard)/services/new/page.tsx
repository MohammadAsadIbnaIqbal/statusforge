"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { useApi } from "@/lib/useApi";

export default function NewServicePage() {
  const { fetchApi } = useApi();
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    description: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await fetchApi("/services", {
        method: "POST",
        body: JSON.stringify(formData),
      });

      router.push("/services");
    } catch (err: unknown) {
      if (err instanceof Error) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const errorObj = err as any;
        if (Array.isArray(errorObj.detail)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setError(errorObj.detail.map((d: any) => d.msg).join(", "));
        } else {
          setError(err.message || "Failed to create service.");
        }
      } else {
        setError("Failed to create service.");
      }
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Add Service</h1>
        <Link href="/services">
          <Button variant="ghost">Cancel</Button>
        </Link>
      </div>

      <Card>
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && <Alert variant="destructive">{error}</Alert>}

            <div className="space-y-4">
              <Input
                id="name"
                label="Service Name"
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g. API Server"
                maxLength={100}
              />

              <div className="flex flex-col space-y-1.5 w-full">
                <label htmlFor="description" className="text-sm font-medium leading-none text-gray-700">
                  Description (Optional)
                </label>
                <textarea
                  id="description"
                  className="flex min-h-[80px] w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus-visible:outline-none focus-visible:border-gray-400 focus-visible:ring-1 focus-visible:ring-gray-900 transition-colors"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="e.g. Main REST API for mobile clients"
                  maxLength={500}
                />
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-4">
              <Link href="/services">
                <Button type="button" variant="outline">Cancel</Button>
              </Link>
              <Button type="submit" isLoading={isLoading}>
                Create Service
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
