"use client";

import { useEffect, useState } from "react";
import { api, getUser } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Usage = { cv_uploaded: number; cv_analyzed: number; ai_call: number; email_sent: number };

const USAGE_LABELS: Record<keyof Usage, string> = {
  cv_uploaded: "CVs uploaded",
  cv_analyzed: "CVs analyzed",
  ai_call: "AI calls",
  email_sent: "Emails sent",
};

export default function SettingsPage() {
  const user = getUser();
  const [fullName, setFullName] = useState("");
  const [orgName, setOrgName] = useState("");
  const [usage, setUsage] = useState<Usage | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Usage>("/api/v1/usage/summary")
      .then(setUsage)
      .catch(() => setUsage(null));
  }, []);

  async function saveProfile() {
    if (!fullName.trim()) return;
    setError("");
    try {
      await api("/api/v1/settings/profile", { method: "PATCH", body: JSON.stringify({ full_name: fullName }) });
      setSuccess("Profile updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile.");
    }
  }

  async function saveOrganization() {
    if (!orgName.trim()) return;
    setError("");
    try {
      await api("/api/v1/settings/organization", { method: "PATCH", body: JSON.stringify({ name: orgName }) });
      setSuccess("Organization updated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update organization. Only owners can do this.");
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-extrabold">Settings</h1>
      <p className="text-sm text-slate-500 mt-1">Account, organization, and usage.</p>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="card mt-6 space-y-3">
        <h2 className="font-bold">Your profile</h2>
        <p className="text-sm text-slate-500">{user?.email}</p>
        <input className="input max-w-sm" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <button className="btn-secondary" onClick={saveProfile}>
          Save profile
        </button>
      </div>

      <div className="card mt-6 space-y-3">
        <h2 className="font-bold">Organization</h2>
        <input className="input max-w-sm" placeholder="Organization name" value={orgName} onChange={(e) => setOrgName(e.target.value)} />
        <button className="btn-secondary" onClick={saveOrganization}>
          Save organization
        </button>
      </div>

      <div className="card mt-6">
        <h2 className="font-bold mb-1">Usage this month</h2>
        <p className="text-xs text-slate-500 mb-4">
          Tracked for future plan sizing — HireFlow doesn&apos;t bill on usage today.
        </p>
        {usage ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {(Object.keys(USAGE_LABELS) as Array<keyof Usage>).map((key) => (
              <div key={key} className="text-center">
                <div className="text-xl font-bold text-electric">{usage[key]}</div>
                <div className="text-xs text-slate-500 mt-1">{USAGE_LABELS[key]}</div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">Usage data unavailable.</p>
        )}
      </div>

      <div className="card mt-6 text-sm text-slate-600">
        Editable email templates live under{" "}
        <a href="/dashboard/templates" className="text-electric font-semibold">
          Templates
        </a>
        . Need help? Email{" "}
        <a href="mailto:support@acreva.com" className="text-electric font-semibold">
          support@acreva.com
        </a>
      </div>
    </div>
  );
}
