"use client";

import React, { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { LoadingSpinner } from "@/components/ui/LoadingSpinner";
import { apiFetch } from "@/lib/api";

export default function EditServicePage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;
  
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    display_order: 0,
    is_visible: true,
  });
  
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    const fetchService = async () => {
      try {
        const token = localStorage.getItem("access_token") || undefined;
        const data = await apiFetch(`/services/${id}`, {}, token);
        if (mounted) {
          setFormData({
            name: data.name,
            description: data.description || "",
            display_order: data.display_order,
            is_visible: data.is_visible,
          });
          setPageLoading(false);
        }
      } catch {
        if (mounted) {
          setError("Failed to load service data.");
          setPageLoading(false);
        }
      }
    };
    fetchService();
    return () => { mounted = false; };
  }, [id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const token = localStorage.getItem("access_token") || undefined;
      await apiFetch(`/services/${id}`, {
        method: "PATCH",
        body: JSON.stringify(formData),
      }, token);
      
      router.push("/services");
    } catch (err: unknown) {
      if (err instanceof Error) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const errorObj = err as any;
        if (Array.isArray(errorObj.detail)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setError(errorObj.detail.map((d: any) => d.msg).join(", "));
        } else {
          setError(err.message || "Failed to update service.");
        }
      } else {
        setError("Failed to update service.");
      }
      setIsLoading(false);
    }
  };

  if (pageLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoadingSpinner className="h-8 w-8 text-gray-400" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Edit Service</h1>
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
                  maxLength={500}
                />
              </div>

              <Input
                id="display_order"
                label="Display Order (lower numbers appear first)"
                type="number"
                required
                value={formData.display_order}
                onChange={(e) => setFormData(prev => ({ ...prev, display_order: parseInt(e.target.value) || 0 }))}
              />

              <div className="flex items-center space-x-2 pt-2">
                <input
                  type="checkbox"
                  id="is_visible"
                  checked={formData.is_visible}
                  onChange={(e) => setFormData(prev => ({ ...prev, is_visible: e.target.checked }))}
                  className="h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                />
                <label htmlFor="is_visible" className="text-sm font-medium text-gray-700">
                  Visible on public status page
                </label>
              </div>
            </div>

            <div className="flex justify-end space-x-2 pt-4">
              <Link href="/services">
                <Button type="button" variant="outline">Cancel</Button>
              </Link>
              <Button type="submit" isLoading={isLoading}>
                Save Changes
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
