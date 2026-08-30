"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { uploadCvBatch } from "@/lib/upload";
import SuccessBanner from "@/components/SuccessBanner";
import ProcessingProgress from "@/components/ProcessingProgress";

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [job, setJob] = useState({ title: "", description: "" });
  const [jobId, setJobId] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [uploadBatchId, setUploadBatchId] = useState<string | null>(null);
  const [scoreBatchId, setScoreBatchId] = useState<string | null>(null);
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
      setUploadBatchId(res.batch_id);
      if (res.rejected.length > 0) {
        setError(`${res.rejected.length} file(s) rejected: ${res.rejected.map((r) => r.filename).join(", ")}`);
      }
    });
  }

  async function runScore() {
    await runStep(async () => {
      const res = await api<{ message?: string; batch_id: string | null }>("/api/v1/scoring/run", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, rescore: true }),
      });
      if (res.batch_id) {
        setScoreBatchId(res.batch_id);
      } else {
        setSuccess(res.message || "No candidates needed scoring.");
        setStep(4);
      }
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

        {step === 2 && !uploadBatchId && (
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
        {step === 2 && uploadBatchId && (
          <ProcessingProgress
            batchId={uploadBatchId}
            onDone={(batch) => {
              setSuccess(`Processed ${batch.completed_count} CV(s).`);
              setStep(3);
            }}
          />
        )}

        {step === 3 && !scoreBatchId && (
          <>
            <p className="text-sm text-slate-600">Run AI scoring against your job description in the background.</p>
            <button className="btn-primary" onClick={runScore} disabled={loading}>
              {loading ? "Starting..." : "Score all candidates"}
            </button>
          </>
        )}
        {step === 3 && scoreBatchId && (
          <ProcessingProgress
            batchId={scoreBatchId}
            onDone={(batch) => {
              setSuccess(`Scored ${batch.completed_count} candidate(s).`);
              setStep(4);
            }}
          />
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
