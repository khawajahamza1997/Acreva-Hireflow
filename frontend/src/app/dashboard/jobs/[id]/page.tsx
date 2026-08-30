"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";
import ProcessingProgress from "@/components/ProcessingProgress";
import {
  StructuredRequirements,
  Weights,
  Thresholds,
  emptyRequirements,
  defaultWeights,
  defaultThresholds,
  rawToFormState,
  weightsToFormState,
  thresholdsToFormState,
  formToStructuredRequirements,
  stableStringify,
} from "@/lib/jobRequirements";

type Job = {
  id: string;
  title: string;
  description: string;
  requirements_version?: number;
  structured_requirements?: Record<string, unknown>;
  scoring_weights?: Record<string, number>;
  score_thresholds?: Record<string, number>;
};

type Dashboard = {
  job_title: string;
  total: number;
  processed: number;
  strong_matches: number;
  shortlisted: number;
  contacted: number;
  failed: number;
  average_score: number | null;
};

function FunnelStep({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col items-center">
      <div className="text-2xl font-extrabold text-electric">{value}</div>
      <div className="text-xs text-slate-500 mt-1 text-center">{label}</div>
    </div>
  );
}

export default function JobOverviewPage() {
  const params = useParams<{ id: string }>();
  const jobId = params.id;

  const [job, setJob] = useState<Job | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [editing, setEditing] = useState(false);
  const [req, setReq] = useState<StructuredRequirements>(emptyRequirements);
  const [weights, setWeights] = useState<Weights>(defaultWeights);
  const [thresholds, setThresholds] = useState<Thresholds>(defaultThresholds);
  const [savingEdit, setSavingEdit] = useState(false);
  const [rescoreBatchId, setRescoreBatchId] = useState<string | null>(null);
  const [rescoring, setRescoring] = useState(false);
  const [confirmingReanalyzeAll, setConfirmingReanalyzeAll] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const [j, d] = await Promise.all([
      api<Job>(`/api/v1/jobs/${jobId}`),
      api<Dashboard>(`/api/v1/jobs/${jobId}/dashboard`),
    ]);
    setJob(j);
    setDashboard(d);
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  function startEditing() {
    if (!job) return;
    setReq(rawToFormState(job.structured_requirements || {}));
    setWeights(weightsToFormState(job.scoring_weights));
    setThresholds(thresholdsToFormState(job.score_thresholds));
    setEditing(true);
  }

  async function saveEdits() {
    if (!job) return;
    setSavingEdit(true);
    setError("");
    try {
      const structured_requirements = formToStructuredRequirements(req);
      const scoring_weights = Object.fromEntries(Object.entries(weights).map(([k, v]) => [k, parseFloat(v) || 0]));
      const score_thresholds = Object.fromEntries(Object.entries(thresholds).map(([k, v]) => [k, parseFloat(v) || 0]));

      const payload: Record<string, unknown> = {};
      if (stableStringify(structured_requirements) !== stableStringify(job.structured_requirements || {})) {
        payload.structured_requirements = structured_requirements;
        payload.requirements_source = "structured";
      }
      if (stableStringify(scoring_weights) !== stableStringify(job.scoring_weights || {})) {
        payload.scoring_weights = scoring_weights;
      }
      if (stableStringify(score_thresholds) !== stableStringify(job.score_thresholds || {})) {
        payload.score_thresholds = score_thresholds;
      }
      if (Object.keys(payload).length === 0) {
        setEditing(false);
        return;
      }

      await api<Job>(`/api/v1/jobs/${jobId}`, { method: "PATCH", body: JSON.stringify(payload) });
      setSuccess(
        payload.structured_requirements
          ? "Requirements updated — a new requirements version was created. Existing scores are unchanged until you rescore."
          : "Scoring configuration updated — already-scored candidates were recalculated instantly."
      );
      setEditing(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setSavingEdit(false);
    }
  }

  async function rescoreWithLatest() {
    setError("");
    setRescoring(true);
    try {
      const res = await api<{ batch_id: string | null; message?: string }>("/api/v1/scoring/run", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, rescore: false }),
      });
      if (res.batch_id) setRescoreBatchId(res.batch_id);
      else {
        setSuccess(res.message || "All candidates are already scored against the latest requirements.");
        setRescoring(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rescore failed.");
      setRescoring(false);
    }
  }

  async function reanalyzeAll() {
    setConfirmingReanalyzeAll(false);
    setError("");
    setRescoring(true);
    try {
      const res = await api<{ batch_id: string | null; message?: string }>("/api/v1/scoring/run", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, rescore: true }),
      });
      if (res.batch_id) setRescoreBatchId(res.batch_id);
      else {
        setSuccess(res.message || "No candidates to re-analyze.");
        setRescoring(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-analysis failed.");
      setRescoring(false);
    }
  }

  if (!job || !dashboard) return <p>Loading…</p>;

  return (
    <div>
      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="card mt-4">
        <h2 className="font-bold mb-4">Screening funnel</h2>
        <div className="flex flex-wrap items-center justify-center gap-6">
          <FunnelStep label="CVs uploaded" value={dashboard.total} />
          <span className="text-slate-300">→</span>
          <FunnelStep label="Analyzed" value={dashboard.processed} />
          <span className="text-slate-300">→</span>
          <FunnelStep label="Strong matches" value={dashboard.strong_matches} />
          <span className="text-slate-300">→</span>
          <FunnelStep label="Shortlisted" value={dashboard.shortlisted} />
          <span className="text-slate-300">→</span>
          <FunnelStep label="Contacted" value={dashboard.contacted} />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-4 border-t border-slate-100">
          <div className="text-center">
            <div className="text-xl font-bold">{dashboard.total}</div>
            <div className="text-xs text-slate-500">Total candidates</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold text-red-600">{dashboard.failed}</div>
            <div className="text-xs text-slate-500">Failed</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold">{dashboard.average_score ?? "—"}</div>
            <div className="text-xs text-slate-500">Average score</div>
          </div>
          <div className="text-center">
            <div className="text-xl font-bold">{dashboard.shortlisted}</div>
            <div className="text-xs text-slate-500">Shortlisted</div>
          </div>
        </div>
      </div>

      <div className="card mt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="font-bold">Requirements &amp; scoring configuration</h2>
          <div className="flex gap-3">
            <button type="button" className="btn-secondary text-sm" onClick={editing ? () => setEditing(false) : startEditing}>
              {editing ? "Cancel edit" : "Edit requirements & weights"}
            </button>
            <button type="button" className="btn-secondary text-sm" onClick={rescoreWithLatest} disabled={rescoring}>
              {rescoring && !rescoreBatchId ? "Starting…" : "Rescore with latest requirements"}
            </button>
            <button type="button" className="btn-secondary text-sm" onClick={() => setConfirmingReanalyzeAll(true)} disabled={rescoring}>
              Re-analyze all
            </button>
          </div>
        </div>

        {confirmingReanalyzeAll && (
          <div className="mt-4 border border-amber-200 bg-amber-50 rounded-xl p-4 text-sm">
            <p className="font-semibold">Re-analyzing {dashboard.total} candidate(s) may consume additional AI credits.</p>
            <div className="mt-3 flex gap-3">
              <button className="btn-secondary" onClick={() => setConfirmingReanalyzeAll(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={reanalyzeAll}>
                Continue
              </button>
            </div>
          </div>
        )}

        {rescoreBatchId && (
          <div className="mt-4">
            <ProcessingProgress
              batchId={rescoreBatchId}
              onDone={(batch) => {
                setSuccess(`Done: ${batch.completed_count} completed, ${batch.failed_count} failed.`);
                setRescoring(false);
                setRescoreBatchId(null);
                load();
              }}
            />
          </div>
        )}

        {!editing && !rescoreBatchId && (
          <p className="text-sm text-slate-500 mt-3">
            Required skills: {(job.structured_requirements?.required_skills as string[] | undefined)?.join(", ") || "—"}
          </p>
        )}

        {editing && (
          <div className="mt-4 space-y-4">
            <div className="grid sm:grid-cols-2 gap-3">
              <input
                className="input"
                placeholder="Required skills (comma-separated)"
                value={req.required_skills}
                onChange={(e) => setReq({ ...req, required_skills: e.target.value })}
              />
              <input
                className="input"
                placeholder="Preferred skills (comma-separated)"
                value={req.preferred_skills}
                onChange={(e) => setReq({ ...req, preferred_skills: e.target.value })}
              />
              <input
                className="input"
                type="number"
                placeholder="Minimum years of experience"
                value={req.min_experience_years}
                onChange={(e) => setReq({ ...req, min_experience_years: e.target.value })}
              />
              <input
                className="input"
                placeholder="Education"
                value={req.education}
                onChange={(e) => setReq({ ...req, education: e.target.value })}
              />
            </div>

            <div>
              <p className="text-sm font-semibold mb-2">Scoring weights</p>
              <div className="grid sm:grid-cols-3 gap-3">
                {(Object.keys(weights) as Array<keyof Weights>).map((key) => (
                  <label key={key} className="text-xs">
                    {key.replace(/_/g, " ")}
                    <input
                      className="input mt-1"
                      type="number"
                      value={weights[key]}
                      onChange={(e) => setWeights({ ...weights, [key]: e.target.value })}
                    />
                  </label>
                ))}
              </div>
            </div>

            <div>
              <p className="text-sm font-semibold mb-2">Match tier thresholds (score ≥ this value)</p>
              <div className="grid sm:grid-cols-3 gap-3">
                <label className="text-xs">
                  Strong Match
                  <input className="input mt-1" type="number" value={thresholds.strong} onChange={(e) => setThresholds({ ...thresholds, strong: e.target.value })} />
                </label>
                <label className="text-xs">
                  Good Match
                  <input className="input mt-1" type="number" value={thresholds.good} onChange={(e) => setThresholds({ ...thresholds, good: e.target.value })} />
                </label>
                <label className="text-xs">
                  Potential Match
                  <input className="input mt-1" type="number" value={thresholds.potential} onChange={(e) => setThresholds({ ...thresholds, potential: e.target.value })} />
                </label>
              </div>
            </div>

            <button className="btn-primary text-sm" disabled={savingEdit} onClick={saveEdits}>
              {savingEdit ? "Saving…" : "Save changes"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
