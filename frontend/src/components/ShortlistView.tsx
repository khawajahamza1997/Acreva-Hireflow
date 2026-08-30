"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, getApiBaseUrl, getToken } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";
import { tierBadgeClass } from "@/lib/tier";

type Candidate = { id: string; name: string; score?: number; score_status?: string };

export default function ShortlistView({ fixedJobId }: { fixedJobId?: string }) {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [topN, setTopN] = useState(5);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  const load = useCallback(async () => {
    const params = new URLSearchParams({ shortlisted: "true" });
    if (fixedJobId) params.set("job_id", fixedJobId);
    setRows(await api<Candidate[]>(`/api/v1/candidates?${params}`));
    setSelected(new Set());
  }, [fixedJobId]);

  useEffect(() => {
    load();
  }, [load]);

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

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function bulkRemove() {
    setError("");
    try {
      const res = await api<{ message: string }>("/api/v1/candidates/bulk-shortlist", {
        method: "POST",
        body: JSON.stringify({ candidate_ids: Array.from(selected), shortlisted: false }),
      });
      setSuccess(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk remove failed.");
    }
  }

  async function exportShortlist() {
    setExporting(true);
    setError("");
    try {
      const apiUrl = getApiBaseUrl();
      const token = getToken();
      const params = new URLSearchParams({ shortlisted: "true" });
      if (fixedJobId) params.set("job_id", fixedJobId);
      const res = await fetch(`${apiUrl}/api/v1/candidates/export?${params}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Export failed.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "shortlist_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      {!fixedJobId && (
        <>
          <h1 className="text-2xl font-extrabold">Shortlist: {rows.length} candidate(s)</h1>
          <p className="text-sm text-slate-500 mt-1">
            Top candidates ready for outreach, based on AI match recommendations. Final selection is yours.
          </p>
        </>
      )}
      {fixedJobId && <p className="text-sm text-slate-500">{rows.length} candidate(s) shortlisted for this job.</p>}

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
        <button className="btn-secondary" onClick={exportShortlist} disabled={exporting || rows.length === 0}>
          {exporting ? "Exporting..." : "Export shortlist"}
        </button>
        {rows.length > 0 && (
          <Link href={`/dashboard/outreach?ids=${rows.map((r) => r.id).join(",")}`} className="btn-secondary">
            Email entire shortlist
          </Link>
        )}
        {selected.size > 0 && (
          <button type="button" className="btn-danger" onClick={bulkRemove}>
            Remove {selected.size} selected
          </button>
        )}
      </div>

      <div className="card mt-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="pb-2">
                <input
                  type="checkbox"
                  checked={rows.length > 0 && selected.size === rows.length}
                  onChange={() => setSelected(selected.size === rows.length ? new Set() : new Set(rows.map((r) => r.id)))}
                />
              </th>
              <th className="pb-2">Name</th>
              <th className="pb-2">Match score</th>
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
                <td className="py-3">
                  <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelected(r.id)} />
                </td>
                <td className="py-3 font-semibold">{r.name}</td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <span>{r.score}/100</span>
                    <span className={`text-xs rounded-full px-2 py-0.5 ${tierBadgeClass(r.score_status)}`}>{r.score_status}</span>
                  </div>
                </td>
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
