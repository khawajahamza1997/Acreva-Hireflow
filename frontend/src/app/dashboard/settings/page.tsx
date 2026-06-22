"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Template = { template_type: string; subject: string; body: string };

export default function SettingsPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Template[]>("/api/v1/email-templates")
      .then(setTemplates)
      .catch((e) => setError(e.message));
  }, []);

  async function saveTemplate(t: Template) {
    setError("");
    try {
      await api(`/api/v1/email-templates/${t.template_type}`, {
        method: "PUT",
        body: JSON.stringify({ subject: t.subject, body: t.body }),
      });
      setSuccess(`Saved ${t.template_type.replace(/_/g, " ")} template.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-extrabold">Settings</h1>
      <p className="text-sm text-slate-500 mt-1">Editable branded email templates.</p>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="space-y-6 mt-6">
        {templates.map((t, idx) => (
          <div key={t.template_type} className="card space-y-3">
            <h2 className="font-bold capitalize">{t.template_type.replace(/_/g, " ")}</h2>
            <input
              className="input"
              value={t.subject}
              onChange={(e) => {
                const copy = [...templates];
                copy[idx] = { ...t, subject: e.target.value };
                setTemplates(copy);
              }}
            />
            <textarea
              className="input min-h-[160px]"
              value={t.body}
              onChange={(e) => {
                const copy = [...templates];
                copy[idx] = { ...t, body: e.target.value };
                setTemplates(copy);
              }}
            />
            <button className="btn-primary" onClick={() => saveTemplate(templates[idx])}>
              Save template
            </button>
          </div>
        ))}
      </div>

      <div className="card mt-8 text-sm text-slate-600">
        Need help? Email{" "}
        <a href="mailto:support@acreva.com" className="text-electric font-semibold">
          support@acreva.com
        </a>
      </div>
    </div>
  );
}
