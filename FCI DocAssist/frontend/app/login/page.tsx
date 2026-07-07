"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ArrowLeft, LogIn, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await register(email, password, fullName);
      } else {
        await login(email, password);
      }
      router.push("/chat");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-fci-mist px-5 py-12 dark:bg-[#0e1310]">
      <div className="w-full max-w-md rounded-lg border border-fci-line bg-white p-6 shadow-soft dark:border-white/10 dark:bg-[#101712]">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-fci-primary hover:text-fci-dark dark:text-fci-light"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Home
        </Link>

        <div className="mt-8">
          <h1 className="text-3xl font-semibold text-fci-ink dark:text-white">
            {mode === "register" ? "Create your account" : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm leading-6 text-fci-steel dark:text-white/70">
            Sign in to keep conversation history, bookmarks, and exports tied to your account.
          </p>
        </div>

        <form onSubmit={submit} className="mt-7 space-y-4">
          {mode === "register" ? (
            <Input
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Full name"
              autoComplete="name"
            />
          ) : null}
          <Input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email"
            type="email"
            autoComplete="email"
            required
          />
          <Input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Password"
            type="password"
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            minLength={8}
            required
          />
          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-400/20 dark:bg-red-400/10 dark:text-red-200">
              {error}
            </div>
          ) : null}
          <Button type="submit" className="w-full" disabled={loading}>
            {mode === "register" ? (
              <UserPlus className="h-4 w-4" aria-hidden="true" />
            ) : (
              <LogIn className="h-4 w-4" aria-hidden="true" />
            )}
            {mode === "register" ? "Create account" : "Sign in"}
          </Button>
        </form>

        <button
          type="button"
          onClick={() => setMode((current) => (current === "login" ? "register" : "login"))}
          className="mt-5 w-full text-sm font-medium text-fci-primary hover:text-fci-dark dark:text-fci-light"
        >
          {mode === "register" ? "Use an existing account" : "Create a new account"}
        </button>
      </div>
    </main>
  );
}
