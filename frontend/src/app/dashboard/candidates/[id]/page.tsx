"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

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
  const [data, setData] = useState<Detail | null>(null);
  const [notes, setNotes] = useState("");

  useEffect(() => {
    api<Detail>(`/api/v1/candidates/${id}`).then((d) => {
      setData(d);
      setNotes(d.notes || "");
    });
  }, [id]);

  async function saveNotes() {
    await api(`/api/v1/candidates/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
  }

  if (!data) return <p>Loading...</p>;

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-extrabold">{data.name}</h1>
      <p className="text-sm text-slate-500">{data.current_role}</p>

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
