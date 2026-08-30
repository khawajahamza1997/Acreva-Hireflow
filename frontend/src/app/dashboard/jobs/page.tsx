"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import SuccessBanner from "@/components/SuccessBanner";
import {
  StructuredRequirements,
  Weights,
  emptyRequirements,
  defaultWeights,
  rawToFormState,
  formToStructuredRequirements,
} from "@/lib/jobRequirements";

type Job = { id: string; title: string; description: string; requirements_version?: number };

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [form, setForm] = useState({ title: "", description: "" });
  const [req, setReq] = useState<StructuredRequirements>(emptyRequirements);
  const [weights, setWeights] = useState<Weights>(defaultWeights);
  const [extracted, setExtracted] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    setJobs(await api<Job[]>("/api/v1/jobs"));
  }

  useEffect(() => {
    load();
  }, []);

  async function extractRequirements() {
    if (form.description.length < 30) return;
    setExtracting(true);
    setError("");
    try {
      const data = await api<Record<string, unknown>>("/api/v1/jobs/extract-requirements", {
        method: "POST",
        body: JSON.stringify({ description: form.description }),
      });
      setReq(rawToFormState(data));
      setExtracted(true);
      setSuccess("Requirements extracted — review and edit below before saving.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not extract requirements.");
    } finally {
      setExtracting(false);
    }
  }

  const weightSum = Object.values(weights).reduce((sum, v) => sum + (parseFloat(v) || 0), 0);

  async function createJob(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const structured_requirements = formToStructuredRequirements(req);
      const scoring_weights = Object.fromEntries(
        Object.entries(weights).map(([k, v]) => [k, parseFloat(v) || 0])
      );
      const hasStructuredContent = Object.values(req).some((v) =>
        typeof v === "boolean" ? v : Boolean(v)
      );
      const requirements_source = extracted ? "extracted" : hasStructuredContent ? "structured" : "freeform";
      const created = await api<Job>("/api/v1/jobs", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          structured_requirements,
          scoring_weights,
          requirements_source,
        }),
      });
      setForm({ title: "", description: "" });
      setReq(emptyRequirements);
      setWeights(defaultWeights);
      setExtracted(false);
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
      <p className="text-sm text-slate-500 mt-1">Create roles to score candidates against. Click a job to open its workspace.</p>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      <div className="grid lg:grid-cols-2 gap-6 mt-6">
        <form onSubmit={createJob} className="card space-y-4">
          <h2 className="font-bold">Create job</h2>
          <input
            className="input"
            placeholder="Job title"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
          <div>
            <textarea
              className="input min-h-[140px]"
              placeholder="Job description (min 30 characters)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
              minLength={30}
            />
            <button
              type="button"
              className="btn-secondary text-sm mt-2"
              disabled={form.description.length < 30 || extracting}
              onClick={extractRequirements}
            >
              {extracting ? "Extracting..." : "Extract requirements from description"}
            </button>
          </div>

          <details className="border border-slate-100 rounded-xl p-4" open={extracted}>
            <summary className="font-semibold text-sm cursor-pointer">Structured requirements (optional)</summary>
            <div className="grid sm:grid-cols-2 gap-3 mt-3">
              <input
                className="input"
                placeholder="Required skills (comma-separated)"
                value={req.required_skills}
                onChange={(e) => setReq({ ...req, required_skills: e.target.value })}
              />
              <input
                className="input"
                placeholder="Preferred skills (comma-separated)"
                value={req.preferred_skills}
                onChange={(e) => setReq({ ...req, preferred_skills: e.target.value })}
              />
              <input
                className="input"
                type="number"
                placeholder="Minimum years of experience"
                value={req.min_experience_years}
                onChange={(e) => setReq({ ...req, min_experience_years: e.target.value })}
              />
              <input
                className="input"
                placeholder="Education (e.g. Bachelor's in CS)"
                value={req.education}
                onChange={(e) => setReq({ ...req, education: e.target.value })}
              />
              <input
                className="input"
                placeholder="Certifications (comma-separated)"
                value={req.certifications}
                onChange={(e) => setReq({ ...req, certifications: e.target.value })}
              />
              <input
                className="input"
                placeholder="Location"
                value={req.location}
                onChange={(e) => setReq({ ...req, location: e.target.value })}
              />
              <select className="input" value={req.work_mode} onChange={(e) => setReq({ ...req, work_mode: e.target.value })}>
                <option value="">Remote / hybrid / on-site</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
                <option value="onsite">On-site</option>
              </select>
              <input
                className="input"
                placeholder="Work authorization requirement"
                value={req.work_authorization}
                onChange={(e) => setReq({ ...req, work_authorization: e.target.value })}
              />
              <input
                className="input"
                type="number"
                placeholder="Salary min"
                value={req.salary_min}
                onChange={(e) => setReq({ ...req, salary_min: e.target.value })}
              />
              <input
                className="input"
                type="number"
                placeholder="Salary max"
                value={req.salary_max}
                onChange={(e) => setReq({ ...req, salary_max: e.target.value })}
              />
              <input
                className="input"
                placeholder="Industry experience"
                value={req.industry}
                onChange={(e) => setReq({ ...req, industry: e.target.value })}
              />
              <input
                className="input"
                placeholder="Languages (comma-separated)"
                value={req.languages}
                onChange={(e) => setReq({ ...req, languages: e.target.value })}
              />
              <input
                className="input"
                placeholder="Notice period"
                value={req.notice_period}
                onChange={(e) => setReq({ ...req, notice_period: e.target.value })}
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={req.management_experience}
                  onChange={(e) => setReq({ ...req, management_experience: e.target.checked })}
                />
                Management/team leadership experience preferred
              </label>
            </div>
          </details>

          <details className="border border-slate-100 rounded-xl p-4">
            <summary className="font-semibold text-sm cursor-pointer">
              Scoring weights ({weightSum}% {weightSum !== 100 && <span className="text-amber-600">— should total 100%</span>})
            </summary>
            <div className="grid sm:grid-cols-2 gap-3 mt-3">
              {(Object.keys(weights) as Array<keyof Weights>).map((key) => (
                <label key={key} className="text-sm">
                  {key.replace(/_/g, " ")}
                  <input
                    className="input mt-1"
                    type="number"
                    value={weights[key]}
                    onChange={(e) => setWeights({ ...weights, [key]: e.target.value })}
                  />
                </label>
              ))}
            </div>
          </details>

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
                <Link href={`/dashboard/jobs/${j.id}`} className="min-w-0">
                  <div className="font-semibold flex items-center gap-2">
                    {j.title}
                    <span className="text-xs font-normal bg-slate-100 text-slate-500 rounded-full px-2 py-0.5">
                      Requirements v{j.requirements_version ?? 1}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1 line-clamp-2">{j.description}</div>
                </Link>
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
