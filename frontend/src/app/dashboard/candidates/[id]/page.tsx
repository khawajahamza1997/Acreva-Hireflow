"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { uploadCallRecording, retryCandidateProcessing, reanalyzeCandidate } from "@/lib/upload";
import SuccessBanner from "@/components/SuccessBanner";
import ProcessingProgress from "@/components/ProcessingProgress";
import { tierBadgeClass, requirementResultIcon, requirementResultClass } from "@/lib/tier";

type RequirementResult = {
  label: string;
  category: string;
  is_hard: boolean;
  result: "meets" | "not_established" | "does_not_meet";
  evidence: string;
};

type EmploymentEntry = { title: string; company: string; start: string; end: string };

type Detail = {
  id: string;
  name: string;
  email: string;
  phone: string;
  location?: string;
  current_role: string;
  skills: string;
  score?: number;
  score_status?: string;
  score_reason?: string;
  score_breakdown?: Record<string, number>;
  requirement_results?: RequirementResult[];
  strengths?: string[];
  concerns?: string[];
  meets_required?: boolean | null;
  employment_history?: EmploymentEntry[];
  certifications?: string[];
  processing_status?: string;
  processing_error?: string;
  notes?: string;
  status: string;
  shortlisted?: boolean;
  cv_download_url?: string;
  call_recording_download_url?: string;
  call_transcript?: string;
  salary_expectation?: string;
  notice_period?: string;
  availability?: string;
  flight_risk_notes?: string;
  history: Array<{ action: string; user_email: string; created_at: string; details: object }>;
};

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<Detail | null>(null);
  const [notes, setNotes] = useState("");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [recordingFile, setRecordingFile] = useState<File | null>(null);
  const [recordingConsent, setRecordingConsent] = useState(false);
  const [uploadingRecording, setUploadingRecording] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [decisionBusy, setDecisionBusy] = useState(false);
  const [confirmingReanalyze, setConfirmingReanalyze] = useState(false);
  const [reanalyzeBatchId, setReanalyzeBatchId] = useState<string | null>(null);

  useEffect(() => {
    api<Detail>(`/api/v1/candidates/${id}`).then((d) => {
      setData(d);
      setNotes(d.notes || "");
    });
  }, [id]);

  async function submitCallRecording() {
    if (!recordingFile || !recordingConsent) return;
    setError("");
    setUploadingRecording(true);
    try {
      await uploadCallRecording(id, recordingFile, recordingConsent);
      const refreshed = await api<Detail>(`/api/v1/candidates/${id}`);
      setData(refreshed);
      setRecordingFile(null);
      setRecordingConsent(false);
      setSuccess("Call recording processed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploadingRecording(false);
    }
  }

  async function saveNotes() {
    setError("");
    try {
      await api(`/api/v1/candidates/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ notes }),
      });
      setSuccess("Notes saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    }
  }

  async function retryProcessing() {
    if (!data) return;
    setError("");
    try {
      const res = await retryCandidateProcessing(data.id);
      setSuccess(res.message);
      setTimeout(async () => setData(await api<Detail>(`/api/v1/candidates/${id}`)), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed.");
    }
  }

  async function setDecision(status: string, shortlisted: boolean) {
    if (!data) return;
    setDecisionBusy(true);
    setError("");
    try {
      await api(`/api/v1/candidates/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status, shortlisted }),
      });
      setData({ ...data, status, shortlisted });
      setSuccess(`Marked as "${status}".`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update decision.");
    } finally {
      setDecisionBusy(false);
    }
  }

  async function startReanalyze() {
    if (!data) return;
    setConfirmingReanalyze(false);
    setError("");
    try {
      const res = await reanalyzeCandidate(data.id);
      setReanalyzeBatchId(res.batch_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start re-analysis.");
    }
  }

  async function removeCandidate() {
    if (!data || !confirm(`Delete ${data.name}? This cannot be undone.`)) return;
    try {
      await api<{ message: string }>(`/api/v1/candidates/${id}`, { method: "DELETE" });
      router.push("/dashboard/candidates");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  if (!data) return <p>Loading...</p>;

  return (
    <div className="max-w-4xl">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link href="/dashboard/candidates" className="text-sm text-electric font-semibold">
            ← Back to candidates
          </Link>
          <h1 className="text-2xl font-extrabold mt-2">{data.name}</h1>
          <p className="text-sm text-slate-500">{data.current_role}</p>
        </div>
        <button type="button" className="btn-danger" onClick={removeCandidate}>
          Delete candidate
        </button>
      </div>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <div className="card space-y-2 text-sm">
          <h2 className="font-bold mb-2">Profile</h2>
          <p>Email: {data.email || "—"}</p>
          <p>Phone: {data.phone || "—"}</p>
          <p>Location: {data.location || "—"}</p>
          <p>Skills: {data.skills || "—"}</p>
          <p>Status: {data.status}</p>
          {data.processing_status && data.processing_status !== "Completed" && (
            <p>
              Processing: <span className="font-semibold">{data.processing_status}</span>
              {data.processing_status === "Failed" && (
                <>
                  {" "}
                  — {data.processing_error}{" "}
                  <button type="button" className="text-electric font-semibold" onClick={retryProcessing}>
                    Retry
                  </button>
                </>
              )}
            </p>
          )}
          {data.cv_download_url && (
            <a href={data.cv_download_url} className="text-electric font-semibold" target="_blank">
              Download original CV
            </a>
          )}
        </div>

        <div className="card">
          <h2 className="font-bold mb-2">Match summary</h2>
          {data.score ? (
            <>
              <div className="flex items-baseline gap-3">
                <div className="text-3xl font-extrabold text-electric">{data.score}/100</div>
                <span className={`text-xs rounded-full px-2 py-0.5 font-semibold ${tierBadgeClass(data.score_status)}`}>
                  {data.score_status}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                AI recommendation — final hiring decision remains with the recruiter.
              </p>
              {data.score_breakdown && Object.keys(data.score_breakdown).length > 0 && (
                <div className="mt-3 space-y-1">
                  {Object.entries(data.score_breakdown).map(([cat, val]) => (
                    <div key={cat} className="flex items-center justify-between text-xs text-slate-500">
                      <span className="capitalize">{cat.replace(/_/g, " ")}</span>
                      <span>{Math.round(val)}/100</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-sm text-slate-500">Not scored yet.</p>
          )}
        </div>
      </div>

      <div className="card mt-6">
        <h2 className="font-bold mb-2">Recruiter decision</h2>
        <p className="text-sm text-slate-500 mb-3">
          AI recommendation: <span className="font-semibold">{data.score_status || "Not scored yet"}</span>. The recruiter
          always makes the final call — the buttons below record your decision separately from the AI result, which is
          never modified.
        </p>
        <div className="flex flex-wrap gap-3">
          <button type="button" className="btn-primary text-sm" disabled={decisionBusy} onClick={() => setDecision("Shortlisted", true)}>
            Shortlist
          </button>
          <button type="button" className="btn-danger text-sm" disabled={decisionBusy} onClick={() => setDecision("Rejected", false)}>
            Reject
          </button>
          <button type="button" className="btn-secondary text-sm" disabled={decisionBusy} onClick={() => setDecision("Review later", false)}>
            Review later
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2">Current status: {data.status}</p>

        <div className="border-t border-slate-100 mt-4 pt-4">
          {!confirmingReanalyze && !reanalyzeBatchId && (
            <button type="button" className="text-sm text-electric font-semibold" onClick={() => setConfirmingReanalyze(true)}>
              Re-analyze this candidate
            </button>
          )}
          {confirmingReanalyze && (
            <div className="border border-amber-200 bg-amber-50 rounded-xl p-4 text-sm">
              <p className="font-semibold">Re-analyzing may consume additional AI credits.</p>
              <div className="mt-3 flex gap-3">
                <button className="btn-secondary" onClick={() => setConfirmingReanalyze(false)}>
                  Cancel
                </button>
                <button className="btn-primary" onClick={startReanalyze}>
                  Continue
                </button>
              </div>
            </div>
          )}
          {reanalyzeBatchId && (
            <ProcessingProgress
              batchId={reanalyzeBatchId}
              onDone={async () => {
                setReanalyzeBatchId(null);
                setSuccess("Re-analysis complete.");
                setData(await api<Detail>(`/api/v1/candidates/${id}`));
              }}
            />
          )}
        </div>
      </div>

      {data.requirement_results && data.requirement_results.length > 0 && (
        <div className="card mt-6 overflow-x-auto">
          <h2 className="font-bold mb-2">Requirement analysis</h2>
          {data.meets_required != null && (
            <p className="text-sm mb-3">
              {data.meets_required ? (
                <span className="text-green-700 font-semibold">✓ Meets all mandatory requirements</span>
              ) : (
                <span className="text-amber-600 font-semibold">⚠ Does not yet clearly meet all mandatory requirements</span>
              )}
            </p>
          )}
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="pb-2">Requirement</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Result</th>
                <th className="pb-2">Evidence</th>
              </tr>
            </thead>
            <tbody>
              {data.requirement_results.map((r, i) => (
                <tr key={i} className="border-b border-slate-50 align-top">
                  <td className="py-2 pr-3">{r.label}</td>
                  <td className="py-2 pr-3 text-xs text-slate-400">{r.is_hard ? "Required" : "Preferred"}</td>
                  <td className={`py-2 pr-3 font-semibold ${requirementResultClass(r.result)}`}>
                    {requirementResultIcon(r.result)}{" "}
                    {r.result === "meets" ? "Meets" : r.result === "does_not_meet" ? "Does not meet" : "Not established from CV"}
                  </td>
                  <td className="py-2 text-slate-500">{r.evidence || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {((data.strengths && data.strengths.length > 0) || (data.concerns && data.concerns.length > 0)) && (
        <div className="grid sm:grid-cols-2 gap-6 mt-6">
          <div className="card">
            <h2 className="font-bold mb-2">Strengths</h2>
            <ul className="text-sm space-y-1.5">
              {(data.strengths || []).map((s, i) => (
                <li key={i} className="text-green-700">
                  ✓ {s}
                </li>
              ))}
              {(!data.strengths || data.strengths.length === 0) && <p className="text-sm text-slate-500">None recorded.</p>}
            </ul>
          </div>
          <div className="card">
            <h2 className="font-bold mb-2">Potential concerns</h2>
            <ul className="text-sm space-y-1.5">
              {(data.concerns || []).map((c, i) => (
                <li key={i} className="text-amber-600">
                  ⚠ {c}
                </li>
              ))}
              {(!data.concerns || data.concerns.length === 0) && <p className="text-sm text-slate-500">None recorded.</p>}
            </ul>
          </div>
        </div>
      )}

      {((data.employment_history && data.employment_history.length > 0) || (data.certifications && data.certifications.length > 0)) && (
        <div className="grid sm:grid-cols-2 gap-6 mt-6">
          {data.employment_history && data.employment_history.length > 0 && (
            <div className="card">
              <h2 className="font-bold mb-2">Experience</h2>
              <div className="space-y-3 text-sm">
                {data.employment_history.map((job, i) => (
                  <div key={i} className="border-b border-slate-50 pb-2 last:border-0">
                    <div className="font-semibold">{job.title || "—"}</div>
                    <div className="text-slate-500">
                      {job.company} {job.start && `· ${job.start} – ${job.end || "Present"}`}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          {data.certifications && data.certifications.length > 0 && (
            <div className="card">
              <h2 className="font-bold mb-2">Certifications</h2>
              <ul className="text-sm space-y-1">
                {data.certifications.map((c, i) => (
                  <li key={i}>• {c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <div className="card mt-6">
        <h2 className="font-bold mb-2">Notes</h2>
        <textarea className="input min-h-[100px]" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <button className="btn-primary mt-3" onClick={saveNotes}>
          Save notes
        </button>
      </div>

      <div className="card mt-6">
        <h2 className="font-bold mb-2">Call intelligence</h2>
        <p className="text-sm text-slate-500 mb-3">
          Upload a call recording or voice note — it&apos;s transcribed and key details are extracted automatically.
        </p>

        {(data.salary_expectation || data.notice_period || data.availability || data.flight_risk_notes) && (
          <div className="grid sm:grid-cols-2 gap-3 text-sm mb-4">
            <p><span className="font-semibold">Salary expectation:</span> {data.salary_expectation || "—"}</p>
            <p><span className="font-semibold">Notice period:</span> {data.notice_period || "—"}</p>
            <p><span className="font-semibold">Availability:</span> {data.availability || "—"}</p>
            <p><span className="font-semibold">Flight-risk notes:</span> {data.flight_risk_notes || "—"}</p>
          </div>
        )}

        {data.call_recording_download_url && (
          <div className="mb-4 space-y-2">
            <a href={data.call_recording_download_url} className="text-electric font-semibold text-sm" target="_blank">
              Play / download recording
            </a>
            {data.call_transcript && (
              <div>
                <button
                  type="button"
                  className="text-sm text-electric font-semibold block"
                  onClick={() => setShowTranscript((v) => !v)}
                >
                  {showTranscript ? "Hide transcript" : "Show transcript"}
                </button>
                {showTranscript && (
                  <p className="text-sm text-slate-600 mt-2 whitespace-pre-wrap">{data.call_transcript}</p>
                )}
              </div>
            )}
          </div>
        )}

        <div className="space-y-2">
          <input
            type="file"
            accept="audio/*"
            className="input"
            onChange={(e) => setRecordingFile(e.target.files?.[0] || null)}
          />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={recordingConsent}
              onChange={(e) => setRecordingConsent(e.target.checked)}
            />
            Candidate is aware this call is being recorded and analyzed.
          </label>
          <button
            type="button"
            className="btn-primary"
            disabled={!recordingFile || !recordingConsent || uploadingRecording}
            onClick={submitCallRecording}
          >
            {uploadingRecording ? "Processing..." : "Upload recording"}
          </button>
        </div>
      </div>

      <div className="card mt-6">
        <h2 className="font-bold mb-4">Activity history</h2>
        <div className="space-y-3 text-sm">
          {data.history.length === 0 && <p className="text-slate-500">No activity yet.</p>}
          {data.history.map((h, i) => (
            <div key={i} className="border-b border-slate-100 pb-2">
              <div className="font-semibold">{h.action.replace(/_/g, " ")}</div>
              <div className="text-slate-500">
                {h.user_email} · {new Date(h.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
