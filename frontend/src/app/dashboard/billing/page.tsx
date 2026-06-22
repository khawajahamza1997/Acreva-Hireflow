"use client";

import { useState } from "react";
import { api } from "@/lib/api";

export default function BillingPage() {
  const [message, setMessage] = useState("");

  async function checkout() {
    try {
      const res = await api<{ checkout_url: string }>("/api/v1/billing/checkout", { method: "POST" });
      window.location.href = res.checkout_url;
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Stripe not configured yet.");
    }
  }

  async function portal() {
    try {
      const res = await api<{ portal_url: string }>("/api/v1/billing/portal", { method: "POST" });
      window.location.href = res.portal_url;
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Billing portal unavailable.");
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-extrabold">Billing</h1>
      <div className="card mt-6">
        <div className="text-sm font-bold text-electric uppercase">Starter plan</div>
        <div className="text-3xl font-extrabold mt-2">
          $39<span className="text-base text-slate-500">/month</span>
        </div>
        <ul className="mt-4 text-sm text-slate-600 space-y-1">
          <li>✓ 14-day free trial included</li>
          <li>✓ AI parsing & scoring</li>
          <li>✓ Team accounts & audit log</li>
        </ul>
        <div className="flex gap-3 mt-6">
          <button className="btn-primary" onClick={checkout}>
            Subscribe with Stripe
          </button>
          <button className="btn-secondary" onClick={portal}>
            Manage billing
          </button>
        </div>
        {message && <p className="text-sm text-orange mt-4">{message}</p>}
      </div>
    </div>
  );
}
