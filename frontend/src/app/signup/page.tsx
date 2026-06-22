"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, setTokens, setUser } from "@/lib/api";

export default function SignUpPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    full_name: "",
    organization_name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const data = await api<{ access_token: string; refresh_token: string; user: object }>(
        "/api/v1/auth/signup",
        { method: "POST", body: JSON.stringify(form) }
      );
      setTokens(data.access_token, data.refresh_token);
      setUser(data.user as Record<string, string>);
      router.push("/dashboard/onboarding");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="card w-full max-w-md">
        <div className="text-xs font-bold text-orange uppercase tracking-wider">14-day free trial</div>
        <h1 className="text-2xl font-extrabold mt-2">Create your workspace</h1>
        <p className="text-sm text-slate-500 mt-1">Set up your organization in under a minute.</p>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {[
            ["full_name", "Your name"],
            ["organization_name", "Company / agency name"],
            ["email", "Work email"],
          ].map(([key, label]) => (
            <div key={key}>
              <label className="label">{label}</label>
              <input
                className="input"
                value={form[key as keyof typeof form]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                required
              />
            </div>
          ))}
          <div>
            <label className="label">Password (min 8 characters)</label>
            <input
              className="input"
              type="password"
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button className="btn-primary w-full" disabled={loading}>
            {loading ? "Creating..." : "Start free trial"}
          </button>
        </form>
        <p className="text-xs text-slate-400 mt-4">
          By signing up you agree to our{" "}
          <Link href="/legal/terms" className="text-electric">
            Terms
          </Link>{" "}
          and{" "}
          <Link href="/legal/privacy" className="text-electric">
            Privacy Policy
          </Link>
          .
        </p>
      </div>
    </div>
  );
}
