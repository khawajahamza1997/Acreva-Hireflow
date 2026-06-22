"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Stats = {
  total: number;
  scored: number;
  shortlisted: number;
  contacted: number;
  interviews: number;
  rejected: number;
  pipeline: Record<string, number>;
  recent: Array<{ name: string; status: string; score?: number }>;
};

export default function DashboardPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Stats>("/api/v1/dashboard/stats")
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!stats) return <p>Loading dashboard...</p>;

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Recruitment overview</h1>
      <p className="text-sm text-slate-500 mt-1">Pipeline health at a glance</p>

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mt-8">
        {[
          ["Total", stats.total],
          ["Scored", stats.scored],
          ["Shortlisted", stats.shortlisted],
          ["Contacted", stats.contacted],
          ["Interviews", stats.interviews],
          ["Rejected", stats.rejected],
        ].map(([label, value]) => (
          <div key={label as string} className="card text-center">
            <div className="text-2xl font-extrabold text-electric">{value}</div>
            <div className="text-xs text-slate-500 mt-1 uppercase tracking-wide">{label}</div>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mt-8">
        <div className="card">
          <h2 className="font-bold mb-4">Pipeline by stage</h2>
          <div className="space-y-2">
            {Object.entries(stats.pipeline).map(([stage, count]) => (
              <div key={stage} className="flex justify-between text-sm">
                <span>{stage}</span>
                <span className="font-bold">{count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h2 className="font-bold mb-4">Recent candidates</h2>
          <div className="space-y-3">
            {stats.recent.map((c, i) => (
              <div key={i} className="flex justify-between text-sm border-b border-slate-100 pb-2">
                <span className="font-semibold">{c.name}</span>
                <span className="text-slate-500">
                  {c.score ? `${c.score}/10 · ` : ""}
                  {c.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
