"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "./api";
import { User } from "../types/api";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let mounted = true;
    const token = localStorage.getItem("access_token");
    if (token) {
      apiFetch("/users/me", {}, token)
        .then((data) => {
          if (mounted) setUser(data);
        })
        .catch(() => {
          localStorage.removeItem("access_token");
          if (mounted) setUser(null);
        })
        .finally(() => {
          if (mounted) setLoading(false);
        });
    } else {
      setTimeout(() => {
        if (mounted) setLoading(false);
      }, 0);
    }
    return () => { mounted = false; };
  }, []);

  const login = (token: string) => {
    localStorage.setItem("access_token", token);
    setLoading(true);
    apiFetch("/users/me", {}, token)
      .then((data) => {
        setUser(data);
        router.push("/dashboard");
      })
      .catch(() => {
        localStorage.removeItem("access_token");
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
