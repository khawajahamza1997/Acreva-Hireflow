"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";

type Job = { id: string; title: string; description: string };

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [form, setForm] = useState({ title: "", description: "" });
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setJobs(await api<Job[]>("/api/v1/jobs"));
  }

  useEffect(() => {
    load();
  }, []);

  async function createJob(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const created = await api<Job>("/api/v1/jobs", { method: "POST", body: JSON.stringify(form) });
      setForm({ title: "", description: "" });
      setSuccess(`Job "${created.title}" created successfully.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job.");
    } finally {
      setLoading(false);
    }
  }

  async function removeJob(job: Job) {
    if (!confirm(`Delete job "${job.title}"? Candidates linked to this job will be kept.`)) return;
    setError("");
    try {
      const res = await api<{ message: string }>(`/api/v1/jobs/${job.id}`, { method: "DELETE" });
      setSuccess(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete job.");
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-extrabold">Jobs</h1>
      <p className="text-sm text-slate-500 mt-1">Create roles to score candidates against.</p>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <form onSubmit={createJob} className="card space-y-4">
          <h2 className="font-bold">Create job</h2>
          <input className="input" placeholder="Job title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
          <textarea className="input min-h-[140px]" placeholder="Job description (min 30 characters)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} required minLength={30} />
          <button className="btn-primary" disabled={loading || form.description.length < 30}>
            {loading ? "Saving..." : "Save job"}
          </button>
        </form>
        <div className="card">
          <h2 className="font-bold mb-4">Your jobs</h2>
          <div className="space-y-3">
            {jobs.length === 0 && <p className="text-sm text-slate-500">No jobs yet. Create your first role.</p>}
            {jobs.map((j) => (
              <div key={j.id} className="border border-slate-100 rounded-xl p-4 flex justify-between gap-3">
                <div>
                  <div className="font-semibold">{j.title}</div>
                  <div className="text-xs text-slate-500 mt-1 line-clamp-2">{j.description}</div>
                </div>
                <button type="button" className="btn-danger shrink-0 self-start" onClick={() => removeJob(j)}>
                  Delete
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
