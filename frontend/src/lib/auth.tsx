"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { User as FirebaseUser, onAuthStateChanged, getIdToken, signOut } from "firebase/auth";
import { auth } from "./firebase";
import { apiFetch } from "./api";
import { User } from "../types/api";

interface AuthContextType {
  user: User | null;
  firebaseUser: FirebaseUser | null;
  loading: boolean;
  token: string | null;
  activeOrganizationId: number | null;
  setActiveOrganizationId: (id: number) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeOrganizationId, setActiveOrganizationId] = useState<number | null>(null);
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setFirebaseUser(currentUser);
      if (currentUser) {
        try {
          const idToken = await getIdToken(currentUser);
          setToken(idToken);
          
          // Bootstrap or fetch user from backend
          const dbUser = await apiFetch("/auth/bootstrap", { method: "POST" }, idToken);
          setUser(dbUser);
          
          // Fetch organizations
          const orgs = await apiFetch("/organizations", {}, idToken);
          if (orgs && orgs.length > 0) {
            setActiveOrganizationId(orgs[0].id);
          }
        } catch (error) {
          console.error("Failed to authenticate with backend", error);
        }
      } else {
        setToken(null);
        setUser(null);
        setActiveOrganizationId(null);
      }
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const logout = async () => {
    await signOut(auth);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, firebaseUser, loading, token, activeOrganizationId, setActiveOrganizationId, logout }}>
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
