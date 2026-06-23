"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { uploadCvBatch } from "@/lib/upload";
import SuccessBanner from "@/components/SuccessBanner";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [job, setJob] = useState({ title: "", description: "" });
  const [jobId, setJobId] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function runStep(action: () => Promise<void>) {
    setLoading(true);
    setError("");
    setSuccess("");
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
      const data = await api<{ id: string; title: string }>("/api/v1/jobs", {
        method: "POST",
        body: JSON.stringify(job),
      });
      setJobId(data.id);
      setSuccess(`Job "${data.title}" created. Upload CVs next (select all 3 sample files at once).`);
      setStep(2);
    });
  }

  async function uploadCvs() {
    if (files.length === 0) return;
    await runStep(async () => {
      const res = await uploadCvBatch(files, jobId);
      setSuccess(res.message + (res.failed ? ` (${res.failed} failed)` : ""));
      setStep(3);
    });
  }

  async function runScore() {
    await runStep(async () => {
      const res = await api<{ message?: string; scored: number }>("/api/v1/scoring/run", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, rescore: true }),
      });
      setSuccess(res.message || `Scored ${res.scored} candidate(s).`);
      setStep(4);
    });
  }

  async function runShortlist() {
    await runStep(async () => {
      const res = await api<{ message: string }>("/api/v1/shortlist/auto", {
        method: "POST",
        body: JSON.stringify({ top_n: 3 }),
      });
      setMessage("Onboarding complete! Explore Dashboard, Outreach, and Pipeline.");
      setSuccess(res.message);
      setStep(5);
    });
  }

  const steps = ["Create job", "Upload CVs", "Score", "Shortlist", "Done"];

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

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

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
            <label className="label">Upload CVs (PDF, DOCX, TXT) — select multiple files</label>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
            {files.length > 0 && (
              <p className="text-xs text-slate-500">{files.length} file(s) selected: {files.map((f) => f.name).join(", ")}</p>
            )}
            <p className="text-xs text-slate-500">
              Tip: select all 3 files from <code className="text-electric">samples/cvs/</code> at once.
            </p>
            <button className="btn-primary" onClick={uploadCvs} disabled={files.length === 0 || loading}>
              {loading ? `Uploading ${files.length} CV(s)...` : `Upload ${files.length || ""} CV(s) & continue`}
            </button>
          </>
        )}

        {step === 3 && (
          <>
            <p className="text-sm text-slate-600">Run AI scoring against your job description (may take 30–60s).</p>
            <button className="btn-primary" onClick={runScore} disabled={loading}>
              {loading ? "Scoring..." : "Score all candidates"}
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
            <button className="btn-primary" onClick={() => router.push("/dashboard/outreach")}>
              Go to Outreach (send email)
            </button>
            <button className="btn-secondary ml-3" onClick={() => router.push("/dashboard")}>
              Go to dashboard
            </button>
          </>
        )}
      </div>
    </div>
  );
}
