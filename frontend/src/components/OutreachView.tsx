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
type SendResult = {
  sent: number;
  failed: number;
  results: Array<{ candidate_id: string; name: string; status: "sent" | "failed"; error?: string }>;
};

export default function OutreachView({ fixedJobId, presetIds }: { fixedJobId?: string; presetIds?: string[] }) {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(presetIds || []));
  const [templates, setTemplates] = useState<Template[]>([]);
  const [emailStatus, setEmailStatus] = useState<EmailStatus | null>(null);
  const [templateType, setTemplateType] = useState("interview_invite");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [demoMode, setDemoMode] = useState(true);
  const [reviewed, setReviewed] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendResult, setSendResult] = useState<SendResult | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams();
    if (presetIds && presetIds.length > 0) {
      params.set("ids", presetIds.join(","));
    } else {
      params.set("shortlisted", "true");
      if (fixedJobId) params.set("job_id", fixedJobId);
    }
    Promise.all([
      api<Candidate[]>(`/api/v1/candidates?${params}`),
      api<Template[]>("/api/v1/email-templates"),
      api<EmailStatus>("/api/v1/outreach/email-status"),
    ])
      .then(([c, t, status]) => {
        setCandidates(c);
        setTemplates(t);
        setEmailStatus(status);
      })
      .catch((e) => setError(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fixedJobId]);

  useEffect(() => {
    const t = templates.find((x) => x.template_type === templateType);
    if (t) {
      setSubject(t.subject);
      setBody(t.body);
    }
    setReviewed(false);
  }, [templateType, templates]);

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setReviewed(false);
  }

  async function reviewEmails() {
    if (selected.size === 0) return;
    setError("");
    const firstId = Array.from(selected)[0];
    try {
      const res = await api<{ subject: string; body: string }>(
        `/api/v1/email-templates/${templateType}/preview?candidate_id=${firstId}`,
        { method: "POST" }
      );
      setSubject(res.subject);
      setBody(res.body);
      setReviewed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed.");
      setReviewed(true);
    }
  }

  async function sendEmails() {
    setSending(true);
    setError("");
    setSuccess("");
    try {
      const res = await api<SendResult>("/api/v1/outreach/send-bulk", {
        method: "POST",
        body: JSON.stringify({
          candidate_ids: Array.from(selected),
          template_type: templateType,
          subject,
          body,
          demo_mode: demoMode,
        }),
      });
      setSendResult(res);
      setConfirming(false);
      setSuccess(demoMode ? "Demo mode — no emails sent." : `${res.sent} sent, ${res.failed} failed.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Send failed.");
    } finally {
      setSending(false);
    }
  }

  async function retryFailed() {
    if (!sendResult) return;
    const failedIds = sendResult.results.filter((r) => r.status === "failed").map((r) => r.candidate_id);
    if (failedIds.length === 0) return;
    setSending(true);
    setError("");
    try {
      const res = await api<SendResult>("/api/v1/outreach/send-bulk", {
        method: "POST",
        body: JSON.stringify({ candidate_ids: failedIds, template_type: templateType, subject, body, demo_mode: demoMode }),
      });
      setSendResult((prev) => {
        if (!prev) return res;
        const merged = prev.results.map((r) => res.results.find((n) => n.candidate_id === r.candidate_id) || r);
        return { sent: merged.filter((r) => r.status === "sent").length, failed: merged.filter((r) => r.status === "failed").length, results: merged };
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="max-w-4xl">
      {!fixedJobId && (
        <>
          <h1 className="text-2xl font-extrabold">Outreach</h1>
          <p className="text-sm text-slate-500 mt-1">
            Select candidates, review the email, then send explicitly — HireFlow never sends on its own.
          </p>
        </>
      )}

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
            {emailStatus.configured ? (emailStatus.test_mode ? "Resend test mode (onboarding@resend.dev)" : "Email ready") : "Email not configured on Render"}
          </p>
          <p className="mt-1">{emailStatus.hint}</p>
        </div>
      )}

      <label className="flex items-center gap-2 mt-4 text-sm">
        <input type="checkbox" checked={demoMode} onChange={(e) => { setDemoMode(e.target.checked); setReviewed(false); setSendResult(null); }} />
        Demo mode (no email sent — safe for dry runs)
      </label>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <div className="card space-y-3">
          <h2 className="font-bold">Select candidates ({selected.size})</h2>
          <div className="max-h-64 overflow-y-auto space-y-1">
            {candidates.length === 0 && <p className="text-xs text-slate-500">No candidates available. Shortlist candidates first.</p>}
            {candidates.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={selected.has(c.id)} onChange={() => toggleSelected(c.id)} />
                {c.name} — {c.email || "no email"}
              </label>
            ))}
          </div>
          <select className="input" value={templateType} onChange={(e) => setTemplateType(e.target.value)}>
            <option value="interview_invite">Interview invitation</option>
            <option value="follow_up">Follow up</option>
            <option value="acknowledgement">Acknowledgement</option>
          </select>
          <button className="btn-secondary" onClick={reviewEmails} disabled={selected.size === 0}>
            Review emails
          </button>
        </div>

        <div className="card space-y-4">
          <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Subject" />
          <textarea className="input min-h-[220px]" value={body} onChange={(e) => setBody(e.target.value)} />
          <p className="text-xs text-slate-500">Placeholder preview shown is for the first selected candidate — each recipient gets their own personalized fields.</p>

          {reviewed && !confirming && !sendResult && (
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold">{selected.size} email(s) ready to send</span>
              <button className="btn-primary" onClick={() => setConfirming(true)} disabled={selected.size === 0}>
                {demoMode ? "Preview send" : `Send ${selected.size} email(s)`}
              </button>
            </div>
          )}

          {confirming && (
            <div className="border border-amber-200 bg-amber-50 rounded-xl p-4 text-sm">
              <p className="font-semibold">
                You are about to send {selected.size} email{selected.size === 1 ? "" : "s"}.
              </p>
              <div className="mt-3 flex gap-3">
                <button className="btn-secondary" onClick={() => setConfirming(false)}>
                  Cancel
                </button>
                <button className="btn-primary" onClick={sendEmails} disabled={sending}>
                  {sending ? "Sending..." : "Send"}
                </button>
              </div>
            </div>
          )}

          {sendResult && (
            <div className="border border-slate-200 rounded-xl p-4 text-sm space-y-2">
              <p className="font-semibold">
                ✓ {sendResult.sent} sent{sendResult.failed > 0 ? ` — ${sendResult.failed} failed` : ""}
              </p>
              {sendResult.results
                .filter((r) => r.status === "failed")
                .map((r) => (
                  <p key={r.candidate_id} className="text-red-600 text-xs">
                    {r.name}: {r.error}
                  </p>
                ))}
              {sendResult.failed > 0 && (
                <button className="btn-secondary text-sm" onClick={retryFailed} disabled={sending}>
                  {sending ? "Retrying..." : "Retry failed"}
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
