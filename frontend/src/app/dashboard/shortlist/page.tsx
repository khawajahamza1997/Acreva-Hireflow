"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Candidate = { id: string; name: string; score?: number; score_status?: string };

export default function ShortlistPage() {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [topN, setTopN] = useState(5);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setRows(await api<Candidate[]>("/api/v1/candidates?shortlisted=true"));
  }

  useEffect(() => {
    load();
  }, []);

  async function autoShortlist() {
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const res = await api<{ message: string }>("/api/v1/shortlist/auto", {
        method: "POST",
        body: JSON.stringify({ top_n: topN }),
      });
      setSuccess(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Shortlist failed.");
    } finally {
      setLoading(false);
    }
  }

  async function removeFromShortlist(candidate: Candidate) {
    setError("");
    try {
      const res = await api<{ message: string }>(`/api/v1/candidates/${candidate.id}/unshortlist`, {
        method: "POST",
      });
      setSuccess(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove from shortlist.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Shortlist</h1>
      <p className="text-sm text-slate-500 mt-1">Top candidates ready for outreach.</p>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="card mt-6 flex flex-wrap items-end gap-4">
        <div>
          <label className="label">Top N candidates</label>
          <input className="input max-w-[100px]" type="number" min={1} max={20} value={topN} onChange={(e) => setTopN(Number(e.target.value))} />
        </div>
        <button className="btn-primary" onClick={autoShortlist} disabled={loading}>
          {loading ? "Shortlisting..." : "Auto-shortlist"}
        </button>
      </div>

      <div className="card mt-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="pb-2">Name</th>
              <th className="pb-2">Score</th>
              <th className="pb-2">Fit</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-slate-500 text-center">
                  No shortlisted candidates yet. Score candidates first, then auto-shortlist.
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-50">
                <td className="py-3 font-semibold">{r.name}</td>
                <td className="py-3">{r.score}/10</td>
                <td className="py-3">{r.score_status}</td>
                <td className="py-3">
                  <button type="button" className="btn-danger" onClick={() => removeFromShortlist(r)}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
