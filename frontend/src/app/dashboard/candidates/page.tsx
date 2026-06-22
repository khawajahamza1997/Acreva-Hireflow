"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

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
  const [file, setFile] = useState<File | null>(null);

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
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    await api("/api/v1/candidates/upload", { method: "POST", body: form });
    setFile(null);
    load();
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

      <form onSubmit={upload} className="card mt-6 flex flex-wrap items-end gap-3">
        <div>
          <label className="label">Upload CV</label>
          <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </div>
        <button className="btn-primary">Parse & save</button>
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
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-50">
                <td className="py-3 font-semibold">{r.name}</td>
                <td className="py-3">{r.current_role}</td>
                <td className="py-3">{r.score ? `${r.score}/10` : "—"}</td>
                <td className="py-3">{r.status}</td>
                <td className="py-3">
                  <Link href={`/dashboard/candidates/${r.id}`} className="text-electric font-semibold">
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
