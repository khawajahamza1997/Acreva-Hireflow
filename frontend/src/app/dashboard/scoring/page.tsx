"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";
import ProcessingProgress from "@/components/ProcessingProgress";

type Job = { id: string; title: string };
type ScoreRunResult = {
  batch_id: string | null;
  total: number;
  skipped: number;
  message?: string;
};

export default function ScoringPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobId, setJobId] = useState("");
  const [batchId, setBatchId] = useState<string | null>(null);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<Job[]>("/api/v1/jobs").then((j) => {
      setJobs(j);
      if (j[0]) setJobId(j[0].id);
    });
  }, []);

  async function run() {
    setLoading(true);
    setError("");
    setSuccess("");
    setBatchId(null);
    try {
      const res = await api<ScoreRunResult>("/api/v1/scoring/run", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, rescore: true }),
      });
      if (res.batch_id) {
        setBatchId(res.batch_id);
      } else {
        setSuccess(res.message || "No candidates needed scoring.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scoring failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Scoring</h1>
      <p className="text-sm text-slate-500 mt-1">
        Score all candidates against a job in the background. Switching jobs re-scores everyone for the new role.
      </p>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="card mt-6 max-w-lg space-y-4">
        <select className="input" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title}
            </option>
          ))}
        </select>
        <button className="btn-primary" onClick={run} disabled={!jobId || loading}>
          {loading ? "Starting..." : "Score all candidates for this job"}
        </button>
      </div>

      {batchId && (
        <div className="mt-6 max-w-lg">
          <ProcessingProgress
            batchId={batchId}
            onDone={(batch) => setSuccess(`Scoring finished: ${batch.completed_count} completed, ${batch.failed_count} failed.`)}
          />
        </div>
      )}
    </div>
  );
}
