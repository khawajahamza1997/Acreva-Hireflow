"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Job = { id: string; title: string };
type Result = { scored: number; results: Array<{ name?: string; score?: number; error?: string }> };

export default function ScoringPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<Job[]>("/api/v1/jobs").then((j) => {
      setJobs(j);
      if (j[0]) setJobId(j[0].id);
    });
  }, []);

  async function run() {
    setLoading(true);
    try {
      setResult(await api<Result>("/api/v1/scoring/run", { method: "POST", body: JSON.stringify({ job_id: jobId }) }));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Scoring</h1>
      <div className="card mt-6 max-w-lg space-y-4">
        <select className="input" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title}
            </option>
          ))}
        </select>
        <button className="btn-primary" onClick={run} disabled={!jobId || loading}>
          {loading ? "Scoring..." : "Score all candidates for this job"}
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
