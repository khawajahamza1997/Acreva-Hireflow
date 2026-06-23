"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { uploadCvBatch } from "@/lib/upload";
import SuccessBanner from "@/components/SuccessBanner";

type Candidate = {
  id: string;
  name: string;
  email: string;
  current_role: string;
  score?: number;
  score_status?: string;
  status: string;
  shortlisted: boolean;
};

export default function CandidatesPage() {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    setRows(await api<Candidate[]>(`/api/v1/candidates?${params}`));
  }, [q, status]);

  useEffect(() => {
    load();
  }, [load]);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (files.length === 0) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      const res = await uploadCvBatch(files);
      setFiles([]);
      setSuccess(res.message + (res.failed ? ` (${res.failed} failed)` : ""));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function removeCandidate(candidate: Candidate) {
    if (!confirm(`Delete ${candidate.name}? This cannot be undone.`)) return;
    setError("");
    try {
      const res = await api<{ message: string }>(`/api/v1/candidates/${candidate.id}`, { method: "DELETE" });
      setSuccess(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Candidates</h1>
      <div className="flex flex-wrap gap-3 mt-4">
        <input className="input max-w-xs" placeholder="Search name, email, role..." value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input max-w-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {["New Applicant", "Scored", "Shortlisted", "Contacted", "Interview Scheduled", "Rejected"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <form onSubmit={upload} className="card mt-6 space-y-3">
        <div>
          <label className="label">Upload CVs (select multiple files)</label>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            multiple
            onChange={(e) => setFiles(Array.from(e.target.files || []))}
          />
          {files.length > 0 && (
            <p className="text-xs text-slate-500 mt-2">{files.length} file(s): {files.map((f) => f.name).join(", ")}</p>
          )}
        </div>
        <button className="btn-primary" disabled={files.length === 0 || uploading}>
          {uploading ? `Uploading ${files.length} CV(s)...` : `Parse & save ${files.length ? `(${files.length})` : ""}`}
        </button>
      </form>

      <div className="card mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="pb-2">Name</th>
              <th className="pb-2">Role</th>
              <th className="pb-2">Score</th>
              <th className="pb-2">Status</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="py-6 text-slate-500 text-center">
                  No candidates yet. Upload CVs to get started.
                </td>
              </tr>
            )}
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-50">
                <td className="py-3 font-semibold">{r.name}</td>
                <td className="py-3">{r.current_role}</td>
                <td className="py-3">{r.score ? `${r.score}/10` : "—"}</td>
                <td className="py-3">{r.status}</td>
                <td className="py-3 space-x-3">
                  <Link href={`/dashboard/candidates/${r.id}`} className="text-electric font-semibold">
                    View
                  </Link>
                  <button type="button" className="text-red-600 font-semibold" onClick={() => removeCandidate(r)}>
                    Delete
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
