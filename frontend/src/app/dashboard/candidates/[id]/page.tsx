"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Detail = {
  id: string;
  name: string;
  email: string;
  phone: string;
  current_role: string;
  skills: string;
  score?: number;
  score_status?: string;
  score_reason?: string;
  notes?: string;
  status: string;
  cv_download_url?: string;
  history: Array<{ action: string; user_email: string; created_at: string; details: object }>;
};

export default function CandidateDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<Detail | null>(null);
  const [notes, setNotes] = useState("");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api<Detail>(`/api/v1/candidates/${id}`).then((d) => {
      setData(d);
      setNotes(d.notes || "");
    });
  }, [id]);

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
          <p>Skills: {data.skills || "—"}</p>
          <p>Status: {data.status}</p>
          {data.cv_download_url && (
            <a href={data.cv_download_url} className="text-electric font-semibold" target="_blank">
              Download original CV
            </a>
          )}
        </div>

        <div className="card">
          <h2 className="font-bold mb-2">AI score</h2>
          {data.score ? (
            <>
              <div className="text-3xl font-extrabold text-electric">{data.score}/10</div>
              <div className="text-sm font-semibold mt-1">{data.score_status}</div>
              <p className="text-sm text-slate-600 mt-3">{data.score_reason}</p>
            </>
          ) : (
            <p className="text-sm text-slate-500">Not scored yet.</p>
          )}
        </div>
      </div>

      <div className="card mt-6">
        <h2 className="font-bold mb-2">Notes</h2>
        <textarea className="input min-h-[100px]" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <button className="btn-primary mt-3" onClick={saveNotes}>
          Save notes
        </button>
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
