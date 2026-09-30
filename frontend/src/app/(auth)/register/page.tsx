"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Activity } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Alert } from "@/components/ui/Alert";
import { useAuth } from "@/lib/auth";
import { apiFetch } from "@/lib/api";

export default function RegisterPage() {
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    organization_name: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.id]: e.target.value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const data = await apiFetch("/register", {
        method: "POST",
        body: JSON.stringify(formData),
      });

      // The backend returns access_token directly on successful registration
      if (data.access_token) {
        login(data.access_token);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const errorObj = err as any;
        if (Array.isArray(errorObj.detail)) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          setError(errorObj.detail.map((d: any) => d.msg).join(", "));
        } else {
          setError(err.message || "Registration failed. Please check your inputs.");
        }
      } else {
        setError("Registration failed. Please check your inputs.");
      }
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center py-12 px-4 sm:px-6 lg:px-8 bg-gray-50">
      <div className="w-full max-w-[400px] space-y-6">
        <div className="flex flex-col items-center space-y-4">
          <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gray-900 text-white shadow-sm">
            <Activity className="h-7 w-7" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-gray-900">Create your account</h1>
            <p className="mt-1.5 text-sm text-gray-500">
              Already have an account?{" "}
              <Link href="/login" className="font-medium text-gray-900 hover:underline hover:underline-offset-4">
                Sign in
              </Link>
            </p>
          </div>
        </div>

        <Card className="shadow-sm border-gray-200">
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && <Alert variant="destructive">{error}</Alert>}
              
              <div className="space-y-4">
                <Input
                  id="organization_name"
                  label="Organization Name"
                  type="text"
                  required
                  value={formData.organization_name}
                  onChange={handleChange}
                  placeholder="e.g. Acme Corp"
                />

                <Input
                  id="username"
                  label="Username"
                  type="text"
                  required
                  value={formData.username}
                  onChange={handleChange}
                  placeholder="e.g. acme-admin"
                />
                
                <Input
                  id="email"
                  label="Email address"
                  type="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="admin@example.com"
                />

                <Input
                  id="password"
                  label="Password"
                  type="password"
                  required
                  value={formData.password}
                  onChange={handleChange}
                  minLength={8}
                />
              </div>

              <Button type="submit" className="w-full" isLoading={isLoading}>
                Create Account
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
