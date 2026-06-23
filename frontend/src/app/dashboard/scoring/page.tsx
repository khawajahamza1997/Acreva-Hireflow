"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Job = { id: string; title: string };
type Result = {
  scored: number;
  message?: string;
  results: Array<{ name?: string; score?: number; error?: string }>;
};

export default function ScoringPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState<Result | null>(null);
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
    setResult(null);
    try {
      const res = await api<Result>("/api/v1/scoring/run", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, rescore: true }),
      });
      setResult(res);
      setSuccess(res.message || `Scored ${res.scored} candidate(s).`);
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
        Score all candidates against a job. Switching jobs re-scores everyone for the new role.
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
          {loading ? "Scoring all candidates (may take 30–60s)..." : "Score all candidates for this job"}
        </button>
      </div>
      {result && (
        <div className="card mt-6">
          <p className="font-semibold">Scored {result.scored} candidate(s)</p>
          <ul className="mt-3 text-sm space-y-1">
            {result.results.map((r, i) => (
              <li key={i}>
                {r.name}: {r.error || `${r.score}/10`}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
