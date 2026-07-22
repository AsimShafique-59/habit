"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

import * as authApi from "@/lib/api/auth";
import { getAccessToken } from "@/lib/auth-storage";
import type { User } from "@/lib/api/auth";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (input: authApi.LoginInput) => Promise<void>;
  signup: (input: authApi.SignupInput) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const profile = await authApi.getProfile();
      setUser(profile);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (input: authApi.LoginInput) => {
    const data = await authApi.login(input);
    setUser(data.user);
  }, []);

  const signup = useCallback(async (input: authApi.SignupInput) => {
    const data = await authApi.signup(input);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider.");
  return ctx;
}
