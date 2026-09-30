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

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append("username", username);
      formData.append("password", password);

      const data = await apiFetch("/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: formData.toString(),
      });

      login(data.access_token);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message || "Invalid username or password");
      } else {
        setError("Invalid username or password");
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
            <h1 className="text-2xl font-semibold tracking-tight text-gray-900">Welcome back</h1>
            <p className="mt-1.5 text-sm text-gray-500">
              Don&apos;t have an account?{" "}
              <Link href="/register" className="font-medium text-gray-900 hover:underline hover:underline-offset-4">
                Sign up
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
                  id="username"
                  label="Username"
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. acme-admin"
                />
                
                <Input
                  id="password"
                  label="Password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <Button type="submit" className="w-full" isLoading={isLoading}>
                Sign in
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
