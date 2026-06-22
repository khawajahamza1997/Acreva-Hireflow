"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [job, setJob] = useState({ title: "", description: "" });
  const [jobId, setJobId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function runStep(action: () => Promise<void>) {
    setLoading(true);
    setError("");
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  async function createJob() {
    await runStep(async () => {
      const data = await api<{ id: string }>("/api/v1/jobs", {
        method: "POST",
        body: JSON.stringify(job),
      });
      setJobId(data.id);
      setStep(2);
    });
  }

  async function uploadCv() {
    if (!file) return;
    await runStep(async () => {
      const form = new FormData();
      form.append("file", file);
      if (jobId) form.append("job_id", jobId);
      await api("/api/v1/candidates/upload", { method: "POST", body: form });
      setStep(3);
    });
  }

  async function runScore() {
    await runStep(async () => {
      await api("/api/v1/scoring/run", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId }),
      });
      setStep(4);
    });
  }

  async function runShortlist() {
    await runStep(async () => {
      await api("/api/v1/shortlist/auto", {
        method: "POST",
        body: JSON.stringify({ top_n: 3 }),
      });
      setMessage("Onboarding complete! Explore Dashboard, Outreach, and Pipeline.");
      setStep(5);
    });
  }

  const steps = ["Create job", "Upload CV", "Score", "Shortlist", "Done"];

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-extrabold">Getting started</h1>
      <p className="text-sm text-slate-500 mt-1">Complete these steps to set up your first hiring workflow.</p>

      <div className="flex gap-2 mt-6 flex-wrap">
        {steps.map((label, i) => (
          <div
            key={label}
            className={`text-xs px-3 py-1 rounded-full font-bold ${
              step > i + 1 ? "bg-green-100 text-green-700" : step === i + 1 ? "bg-electric text-white" : "bg-slate-100 text-slate-500"
            }`}
          >
            {i + 1}. {label}
          </div>
        ))}
      </div>

      {error && <p className="text-sm text-red-600 mt-4">{error}</p>}

      <div className="card mt-8 space-y-4">
        {step === 1 && (
          <>
            <div>
              <label className="label">Job title</label>
              <input className="input" value={job.title} onChange={(e) => setJob({ ...job, title: e.target.value })} />
            </div>
            <div>
              <label className="label">Job description</label>
              <textarea
                className="input min-h-[160px]"
                value={job.description}
                onChange={(e) => setJob({ ...job, description: e.target.value })}
              />
            </div>
            <button className="btn-primary" onClick={createJob} disabled={job.description.length < 30 || loading}>
              {loading ? "Saving..." : "Continue"}
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <label className="label">Upload a CV (PDF, DOCX, TXT)</label>
            <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setFile(e.target.files?.[0] || null)} />
            <button className="btn-primary" onClick={uploadCv} disabled={!file || loading}>
              {loading ? "Uploading..." : "Upload & continue"}
            </button>
          </>
        )}

        {step === 3 && (
          <>
            <p className="text-sm text-slate-600">Run AI scoring against your job description.</p>
            <button className="btn-primary" onClick={runScore} disabled={loading}>
              {loading ? "Scoring..." : "Score candidates"}
            </button>
          </>
        )}

        {step === 4 && (
          <>
            <p className="text-sm text-slate-600">Auto-shortlist your top 3 candidates.</p>
            <button className="btn-primary" onClick={runShortlist} disabled={loading}>
              {loading ? "Shortlisting..." : "Shortlist top 3"}
            </button>
          </>
        )}

        {step === 5 && (
          <>
            <p className="text-green-700 font-semibold">{message}</p>
            <button className="btn-primary" onClick={() => router.push("/dashboard")}>
              Go to dashboard
            </button>
          </>
        )}
      </div>
    </div>
  );
}
