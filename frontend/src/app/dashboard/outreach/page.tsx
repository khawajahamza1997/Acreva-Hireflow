"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Candidate = { id: string; name: string; email: string };
type Template = { template_type: string; subject: string; body: string };
type EmailStatus = {
  configured: boolean;
  test_mode: boolean;
  from_address: string;
  your_email: string;
  allowed_test_recipient: string | null;
  hint: string;
};

export default function OutreachPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [emailStatus, setEmailStatus] = useState<EmailStatus | null>(null);
  const [candidateId, setCandidateId] = useState("");
  const [templateType, setTemplateType] = useState("interview_invite");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [demoMode, setDemoMode] = useState(true);
  const [sendTestEmail, setSendTestEmail] = useState(true);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const testRecipient =
    emailStatus?.allowed_test_recipient || emailStatus?.your_email || "your Resend signup email";

  useEffect(() => {
    Promise.all([
      api<Candidate[]>("/api/v1/candidates?shortlisted=true"),
      api<Template[]>("/api/v1/email-templates"),
      api<EmailStatus>("/api/v1/outreach/email-status"),
    ])
      .then(([c, t, status]) => {
        setCandidates(c);
        setTemplates(t);
        setEmailStatus(status);
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

  useEffect(() => {
    if (!candidateId || !templateType) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api<{ subject: string; body: string }>(
          `/api/v1/email-templates/${templateType}/preview?candidate_id=${candidateId}`,
          { method: "POST" }
        );
        if (!cancelled) {
          setSubject(res.subject);
          setBody(res.body);
        }
      } catch {
        /* keep template text; send still fills placeholders on the server */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [candidateId, templateType]);

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
      const payload: Record<string, unknown> = {
        candidate_id: candidateId,
        template_type: templateType,
        subject,
        body,
        demo_mode: demoMode,
      };
      if (!demoMode && sendTestEmail && emailStatus?.test_mode) {
        payload.send_to_email = testRecipient;
      } else if (!demoMode && sendTestEmail) {
        payload.send_to_email = emailStatus?.your_email;
      }

      const res = await api<{ success: boolean; demo?: boolean; message?: string }>("/api/v1/outreach/send", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSuccess(res.message || (res.demo ? "Demo mode — email not sent." : "Email sent successfully."));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-extrabold">Outreach</h1>

      {emailStatus && (
        <div
          className={`mt-4 rounded-xl border px-4 py-3 text-sm ${
            emailStatus.configured
              ? emailStatus.test_mode
                ? "bg-amber-50 border-amber-200 text-amber-900"
                : "bg-green-50 border-green-200 text-green-800"
              : "bg-amber-50 border-amber-200 text-amber-900"
          }`}
        >
          <p className="font-semibold">
            {emailStatus.configured
              ? emailStatus.test_mode
                ? "Resend test mode (onboarding@resend.dev)"
                : "Email ready"
              : "Email not configured on Render"}
          </p>
          <p className="mt-1">{emailStatus.hint}</p>
          {emailStatus.test_mode && !emailStatus.allowed_test_recipient && (
            <p className="mt-2 text-xs">
              Render env: <code>RESEND_TEST_TO_EMAIL=khawajahamzaj@gmail.com</code>
            </p>
          )}
        </div>
      )}

      <label className="flex items-center gap-2 mt-4 text-sm">
        <input type="checkbox" checked={demoMode} onChange={(e) => setDemoMode(e.target.checked)} />
        Demo mode (no email sent — safe for dry runs)
      </label>
      {!demoMode && (
        <label className="flex items-center gap-2 mt-2 text-sm">
          <input type="checkbox" checked={sendTestEmail} onChange={(e) => setSendTestEmail(e.target.checked)} />
          {emailStatus?.test_mode
            ? `Send test email to ${testRecipient} (required by Resend test mode)`
            : `Send to my inbox (${emailStatus?.your_email}) for video demo`}
        </label>
      )}

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
            {loading ? "Sending..." : demoMode ? "Preview send" : "Send real email"}
          </button>
        </div>
      </div>
    </div>
  );
}
