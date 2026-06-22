"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Candidate = { id: string; name: string; score?: number; score_status?: string };

export default function ShortlistPage() {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [topN, setTopN] = useState(5);
  const [message, setMessage] = useState("");

  async function load() {
    setRows(await api<Candidate[]>("/api/v1/candidates?shortlisted=true"));
  }

  useEffect(() => {
    load();
  }, []);

  async function autoShortlist() {
    const res = await api<{ count: number; names: string[] }>("/api/v1/shortlist/auto", {
      method: "POST",
      body: JSON.stringify({ top_n: topN }),
    });
    setMessage(`Shortlisted ${res.count}: ${res.names.join(", ")}`);
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Shortlist</h1>
      <div className="card mt-6 flex flex-wrap items-end gap-4">
        <div>
          <label className="label">Top N candidates</label>
          <input className="input max-w-[100px]" type="number" min={1} max={20} value={topN} onChange={(e) => setTopN(Number(e.target.value))} />
        </div>
        <button className="btn-primary" onClick={autoShortlist}>
          Auto-shortlist
        </button>
      </div>
      {message && <p className="text-green-700 mt-4 text-sm font-semibold">{message}</p>}
      <div className="card mt-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="pb-2">Name</th>
              <th className="pb-2">Score</th>
              <th className="pb-2">Fit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-50">
                <td className="py-3 font-semibold">{r.name}</td>
                <td className="py-3">{r.score}/10</td>
                <td className="py-3">{r.score_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
