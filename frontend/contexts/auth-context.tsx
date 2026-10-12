"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

type AuthContextValue = {
  token: string | null;
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = window.localStorage.getItem("fci-token");
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    api
      .me(stored)
      .then(setUser)
      .catch(() => {
        window.localStorage.removeItem("fci-token");
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const persistSession = useCallback((accessToken: string, nextUser: User) => {
    window.localStorage.setItem("fci-token", accessToken);
    setToken(accessToken);
    setUser(nextUser);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await api.login({ email, password });
      persistSession(response.access_token, response.user);
    },
    [persistSession],
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const response = await api.register({
        email,
        password,
        full_name: fullName,
      });
      persistSession(response.access_token, response.user);
    },
    [persistSession],
  );

  const logout = useCallback(() => {
    window.localStorage.removeItem("fci-token");
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ token, user, loading, login, register, logout }),
    [token, user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
