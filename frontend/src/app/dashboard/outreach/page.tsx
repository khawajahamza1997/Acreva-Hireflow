"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Candidate = { id: string; name: string; email: string };
type Template = { template_type: string; subject: string; body: string };

export default function OutreachPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [candidateId, setCandidateId] = useState("");
  const [templateType, setTemplateType] = useState("interview_invite");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [demoMode, setDemoMode] = useState(true);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      api<Candidate[]>("/api/v1/candidates?shortlisted=true"),
      api<Template[]>("/api/v1/email-templates"),
    ])
      .then(([c, t]) => {
        setCandidates(c);
        setTemplates(t);
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    const t = templates.find((x) => x.template_type === templateType);
    if (t) {
      setSubject(t.subject);
      setBody(t.body);
    }
  }, [templateType, templates]);

  async function preview() {
    if (!candidateId) return;
    setError("");
    try {
      const res = await api<{ subject: string; body: string }>(
        `/api/v1/email-templates/${templateType}/preview?candidate_id=${candidateId}`,
        { method: "POST" }
      );
      setSubject(res.subject);
      setBody(res.body);
      setSuccess("Template filled for candidate.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed.");
    }
  }

  async function send() {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const res = await api<{ success: boolean; demo?: boolean; message?: string }>("/api/v1/outreach/send", {
        method: "POST",
        body: JSON.stringify({ candidate_id: candidateId, template_type: templateType, subject, body, demo_mode: demoMode }),
      });
      setSuccess(res.demo ? "Demo mode — email not sent." : "Email sent successfully.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-extrabold">Outreach</h1>
      <label className="flex items-center gap-2 mt-4 text-sm">
        <input type="checkbox" checked={demoMode} onChange={(e) => setDemoMode(e.target.checked)} />
        Demo mode (preview only — safe for presentations)
      </label>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <div className="card space-y-4">
          <select className="input" value={candidateId} onChange={(e) => setCandidateId(e.target.value)}>
            <option value="">Select shortlisted candidate</option>
            {candidates.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} — {c.email || "no email"}
              </option>
            ))}
          </select>
          {candidates.length === 0 && (
            <p className="text-xs text-slate-500">Shortlist candidates first from the Shortlist page.</p>
          )}
          <select className="input" value={templateType} onChange={(e) => setTemplateType(e.target.value)}>
            <option value="interview_invite">Interview invitation</option>
            <option value="follow_up">Follow up</option>
            <option value="acknowledgement">Acknowledgement</option>
          </select>
          <button className="btn-secondary" onClick={preview} disabled={!candidateId}>
            Fill template for candidate
          </button>
        </div>
        <div className="card space-y-4">
          <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" />
          <textarea className="input min-h-[220px]" value={body} onChange={(e) => setBody(e.target.value)} />
          <button className="btn-primary" onClick={send} disabled={!candidateId || loading}>
            {loading ? "Sending..." : demoMode ? "Preview send" : "Send email"}
          </button>
        </div>
      </div>
    </div>
  );
}
