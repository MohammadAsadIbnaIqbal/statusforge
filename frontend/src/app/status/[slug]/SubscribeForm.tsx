"use client";

import React, { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Alert } from "@/components/ui/Alert";
import { apiFetch } from "@/lib/api";

export function SubscribeForm({ slug }: { slug: string }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setStatus("loading");
    setMessage("");

    try {
      const data = await apiFetch(`/status/${slug}/subscribe`, {
        method: "POST",
        body: JSON.stringify({ email }),
      });
      setStatus("success");
      setMessage(data.message || "Please check your email to confirm your subscription.");
      setEmail("");
    } catch (err: unknown) {
      setStatus("error");
      if (err instanceof Error) {
        if (err.message.includes("already subscribed")) {
          setMessage("This email is already subscribed.");
        } else {
          setMessage(err.message);
        }
      } else {
        setMessage("Failed to subscribe. Please try again.");
      }
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-medium text-gray-900 mb-2">Subscribe to Updates</h3>
      <p className="text-sm text-gray-500 mb-4">
        Get email notifications whenever StatusForge creates, updates or resolves an incident.
      </p>
      
      {status === "success" ? (
        <Alert variant="success" title="Subscribed successfully">{message}</Alert>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={status === "loading"}
              className="w-full"
            />
          </div>
          <Button type="submit" disabled={status === "loading" || !email}>
            {status === "loading" ? "Subscribing..." : "Subscribe"}
          </Button>
        </form>
      )}
      
      {status === "error" && (
        <div className="mt-3">
          <Alert variant="destructive" title="Subscription failed">{message}</Alert>
        </div>
      )}
    </div>
  );
}
