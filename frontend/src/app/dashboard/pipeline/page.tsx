"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type Candidate = {
  id: string;
  name: string;
  current_role: string;
  score?: number;
  status: string;
  interview_date?: string;
  interview_stage?: string;
};

const STAGES = ["New Applicant", "Scored", "Shortlisted", "Contacted", "Interview Scheduled", "Rejected"];

export default function PipelinePage() {
  const [rows, setRows] = useState<Candidate[]>([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    const params = q ? `?q=${encodeURIComponent(q)}` : "";
    api<Candidate[]>(`/api/v1/candidates${params}`).then(setRows);
  }, [q]);

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Pipeline</h1>
      <input className="input max-w-sm mt-4" placeholder="Filter candidates..." value={q} onChange={(e) => setQ(e.target.value)} />

      <div className="grid lg:grid-cols-3 xl:grid-cols-6 gap-4 mt-6">
        {STAGES.map((stage) => {
          const items = rows.filter((r) => r.status === stage);
          return (
            <div key={stage} className="card p-4 min-h-[240px]">
              <div className="text-xs font-bold uppercase text-slate-500 mb-3">
                {stage} ({items.length})
              </div>
              <div className="space-y-2">
                {items.map((c) => (
                  <Link
                    key={c.id}
                    href={`/dashboard/candidates/${c.id}`}
                    className="block rounded-lg bg-page p-2 text-xs hover:ring-2 hover:ring-electric/20"
                  >
                    <div className="font-semibold">{c.name}</div>
                    {c.score ? <div className="text-electric">{c.score}/10</div> : null}
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
