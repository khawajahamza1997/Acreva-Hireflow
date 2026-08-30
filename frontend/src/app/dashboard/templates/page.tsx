"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Template = { template_type: string; subject: string; body: string };

const LABELS: Record<string, string> = {
  interview_invite: "Interview invitation",
  follow_up: "Follow up",
  acknowledgement: "Application acknowledgement",
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [selected, setSelected] = useState("interview_invite");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const data = await api<Template[]>("/api/v1/email-templates");
    setTemplates(data);
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const t = templates.find((x) => x.template_type === selected);
    if (t) {
      setSubject(t.subject);
      setBody(t.body);
    }
  }, [selected, templates]);

  async function save() {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await api(`/api/v1/email-templates/${selected}`, {
        method: "PUT",
        body: JSON.stringify({ subject, body }),
      });
      setSuccess("Template saved.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save template.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-extrabold">Email templates</h1>
      <p className="text-sm text-slate-500 mt-1">
        Edit the default templates used in Outreach. Supported placeholders: {"{candidate_name}"}, {"{job_title}"},{" "}
        {"{company_name}"}, {"{recruiter_name}"}, {"{interview_date}"}, {"{interview_time}"}, {"{interview_format}"}.
      </p>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="flex gap-2 mt-6">
        {Object.keys(LABELS).map((type) => (
          <button
            key={type}
            type="button"
            onClick={() => setSelected(type)}
            className={`text-sm px-3 py-1.5 rounded-full font-semibold ${
              selected === type ? "bg-electric text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {LABELS[type]}
          </button>
        ))}
      </div>

      <div className="card mt-4 space-y-4">
        <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" />
        <textarea className="input min-h-[280px]" value={body} onChange={(e) => setBody(e.target.value)} />
        <button className="btn-primary" onClick={save} disabled={saving}>
          {saving ? "Saving..." : "Save template"}
        </button>
      </div>
    </div>
  );
}
