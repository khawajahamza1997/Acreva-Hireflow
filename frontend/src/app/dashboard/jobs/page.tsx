"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Job = { id: string; title: string; description: string };

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [form, setForm] = useState({ title: "", description: "" });

  async function load() {
    setJobs(await api<Job[]>("/api/v1/jobs"));
  }

  useEffect(() => {
    load();
  }, []);

  async function createJob(e: React.FormEvent) {
    e.preventDefault();
    await api("/api/v1/jobs", { method: "POST", body: JSON.stringify(form) });
    setForm({ title: "", description: "" });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Jobs</h1>
      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <form onSubmit={createJob} className="card space-y-4">
          <h2 className="font-bold">Create job</h2>
          <input className="input" placeholder="Job title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          <textarea className="input min-h-[140px]" placeholder="Job description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required />
          <button className="btn-primary">Save job</button>
        </form>
        <div className="card">
          <h2 className="font-bold mb-4">Your jobs</h2>
          <div className="space-y-3">
            {jobs.map((j) => (
              <div key={j.id} className="border border-slate-100 rounded-xl p-4">
                <div className="font-semibold">{j.title}</div>
                <div className="text-xs text-slate-500 mt-1 line-clamp-2">{j.description}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
