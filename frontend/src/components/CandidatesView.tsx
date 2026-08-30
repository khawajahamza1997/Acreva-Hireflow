"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { api, getApiBaseUrl, getToken } from "@/lib/api";
import { uploadCvBatch, retryCandidateProcessing, DuplicateCandidate } from "@/lib/upload";
import SuccessBanner from "@/components/SuccessBanner";
import ProcessingProgress from "@/components/ProcessingProgress";
import { tierBadgeClass, TIER_OPTIONS } from "@/lib/tier";

type RequirementResult = { label: string; category: string; is_hard: boolean; result: string };

type Candidate = {
  id: string;
  name: string;
  email: string;
  current_role: string;
  score?: number;
  score_status?: string;
  status: string;
  shortlisted: boolean;
  experience_years?: number;
  education?: string;
  skills?: string;
  requirement_results?: RequirementResult[];
  processing_status?: string;
  processing_error?: string;
  meets_required?: boolean | null;
};

type Job = { id: string; title: string };

const PROCESSING_STATUS_OPTIONS = ["Queued", "Extracting", "Analyzing", "Scoring", "Completed", "Failed", "Needs review"];
const STATUS_OPTIONS = ["New Applicant", "Scored", "Shortlisted", "Contacted", "Interview Scheduled", "Review later", "Rejected"];

const emptyFilters = {
  minScore: "",
  maxScore: "",
  tier: "",
  meetsRequired: "",
  skills: "",
  minExperience: "",
  education: "",
  location: "",
  workAuthorization: "",
  jobId: "",
  processingStatus: "",
};

function topSkills(skills?: string, max = 3): string {
  if (!skills) return "—";
  const list = skills.split(",").map((s) => s.trim()).filter(Boolean);
  return list.length ? list.slice(0, max).join(", ") : "—";
}

function missingRequirements(results?: RequirementResult[]): string {
  const missing = (results || []).filter((r) => r.is_hard && r.result !== "meets").map((r) => r.label);
  return missing.length ? missing.join(", ") : "None identified";
}

export default function CandidatesView({ fixedJobId }: { fixedJobId?: string }) {
  const router = useRouter();
  const [rows, setRows] = useState<Candidate[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [filters, setFilters] = useState({ ...emptyFilters, jobId: fixedJobId || "" });
  const [files, setFiles] = useState<File[]>([]);
  const [uploadJobId, setUploadJobId] = useState(fixedJobId || "");
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);

  const load = useCallback(async () => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (status) params.set("status", status);
    if (filters.minScore) params.set("min_score", filters.minScore);
    if (filters.maxScore) params.set("max_score", filters.maxScore);
    if (filters.tier) params.set("tier", filters.tier);
    if (filters.meetsRequired) params.set("meets_required", filters.meetsRequired);
    if (filters.skills) params.set("skills", filters.skills);
    if (filters.minExperience) params.set("min_experience_years", filters.minExperience);
    if (filters.education) params.set("education", filters.education);
    if (filters.location) params.set("location", filters.location);
    if (filters.workAuthorization) params.set("work_authorization", filters.workAuthorization);
    if (fixedJobId) params.set("job_id", fixedJobId);
    else if (filters.jobId) params.set("job_id", filters.jobId);
    if (filters.processingStatus) params.set("processing_status", filters.processingStatus);
    params.set("sort", sort);
    params.set("order", order);
    setRows(await api<Candidate[]>(`/api/v1/candidates?${params}`));
  }, [q, status, filters, sort, order, fixedJobId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    api<Job[]>("/api/v1/jobs").then(setJobs).catch(() => {});
  }, []);

  async function upload(e: React.FormEvent) {
    e.preventDefault();
    if (files.length === 0) return;
    setUploading(true);
    setError("");
    setSuccess("");
    setDuplicates([]);
    try {
      const res = await uploadCvBatch(files, uploadJobId || undefined);
      setFiles([]);
      if (res.batch_id) setBatchId(res.batch_id);
      setDuplicates(res.duplicates || []);
      if (res.rejected.length > 0) {
        setError(`${res.rejected.length} file(s) rejected: ${res.rejected.map((r) => `${r.filename} (${r.error})`).join(", ")}`);
      }
      if (!res.batch_id && (!res.duplicates || res.duplicates.length === 0)) {
        setError("No files were accepted.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function uploadDuplicateAsNew(dup: DuplicateCandidate) {
    const file = files.find((f) => f.name === dup.filename);
    // files may already be cleared after the batch call; re-select isn't tracked, so just
    // acknowledge and let the recruiter know they should re-pick that file if needed.
    setDuplicates((prev) => prev.filter((d) => d.filename !== dup.filename));
    if (!file) {
      setError(`Please re-select "${dup.filename}" and upload again to force it in as a new candidate.`);
      return;
    }
    try {
      const res = await uploadCvBatch([file], uploadJobId || undefined, [dup.filename]);
      if (res.batch_id) setBatchId(res.batch_id);
      setSuccess(`Uploading "${dup.filename}" as a new candidate.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    }
  }

  async function removeCandidate(candidate: Candidate) {
    if (!confirm(`Delete ${candidate.name}? This cannot be undone.`)) return;
    setError("");
    try {
      const res = await api<{ message: string }>(`/api/v1/candidates/${candidate.id}`, { method: "DELETE" });
      setSuccess(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  function toggleSort(key: string) {
    if (sort === key) {
      setOrder(order === "asc" ? "desc" : "asc");
    } else {
      setSort(key);
      setOrder(key === "name" || key === "education" ? "asc" : "desc");
    }
  }

  function toggleSelected(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll() {
    setSelected((prev) => (prev.size === rows.length ? new Set() : new Set(rows.map((r) => r.id))));
  }

  async function bulkShortlist(shortlisted: boolean) {
    setBulkBusy(true);
    setError("");
    try {
      const res = await api<{ message: string }>("/api/v1/candidates/bulk-shortlist", {
        method: "POST",
        body: JSON.stringify({ candidate_ids: Array.from(selected), shortlisted }),
      });
      setSuccess(res.message);
      setSelected(new Set());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk shortlist failed.");
    } finally {
      setBulkBusy(false);
    }
  }

  async function bulkRetry() {
    setBulkBusy(true);
    setError("");
    try {
      const res = await api<{ message: string }>("/api/v1/candidates/retry-processing-bulk", {
        method: "POST",
        body: JSON.stringify({ candidate_ids: Array.from(selected) }),
      });
      setSuccess(res.message);
      setSelected(new Set());
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk retry failed.");
    } finally {
      setBulkBusy(false);
    }
  }

  async function retryOne(id: string) {
    setError("");
    try {
      const res = await retryCandidateProcessing(id);
      setSuccess(res.message);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Retry failed.");
    }
  }

  function compareSelected() {
    const ids = Array.from(selected);
    if (ids.length < 2 || ids.length > 10) return;
    router.push(`/dashboard/candidates/compare?ids=${ids.join(",")}`);
  }

  async function exportSelected() {
    setBulkBusy(true);
    setError("");
    try {
      const apiUrl = getApiBaseUrl();
      const token = getToken();
      const params = new URLSearchParams();
      if (selected.size > 0) params.set("candidate_ids", Array.from(selected).join(","));
      else if (fixedJobId) params.set("job_id", fixedJobId);
      const res = await fetch(`${apiUrl}/api/v1/candidates/export?${params}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error("Export failed.");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "candidates_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed.");
    } finally {
      setBulkBusy(false);
    }
  }

  const filterChips: Array<{ key: keyof typeof emptyFilters; label: string }> = [
    { key: "minScore", label: `Score ≥ ${filters.minScore}` },
    { key: "maxScore", label: `Score ≤ ${filters.maxScore}` },
    { key: "tier", label: filters.tier },
    { key: "meetsRequired", label: filters.meetsRequired === "true" ? "Meets all mandatory requirements" : "Missing requirements" },
    { key: "skills", label: `Skill: ${filters.skills}` },
    { key: "minExperience", label: `${filters.minExperience}+ years experience` },
    { key: "education", label: `Education: ${filters.education}` },
    { key: "location", label: `Location: ${filters.location}` },
    { key: "workAuthorization", label: `Work auth: ${filters.workAuthorization}` },
    ...(fixedJobId ? [] : [{ key: "jobId" as const, label: jobs.find((j) => j.id === filters.jobId)?.title || "" }]),
    { key: "processingStatus", label: `Processing: ${filters.processingStatus}` },
  ];
  const activeFilters = filterChips.filter((f) => filters[f.key]);

  return (
    <div>
      {!fixedJobId && (
        <>
          <h1 className="text-2xl font-extrabold">Candidates</h1>
          <p className="text-sm text-slate-500 mt-1">
            AI-assisted screening — match scores are recommendations. The final hiring decision is yours.
          </p>
        </>
      )}

      <div className="flex flex-wrap gap-3 mt-4">
        <input className="input max-w-xs" placeholder="Search name, email, skill, company..." value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input max-w-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="card mt-4 space-y-3">
        <h2 className="font-bold text-sm">Filters</h2>
        <div className="grid sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {!fixedJobId && (
            <select className="input" value={filters.jobId} onChange={(e) => setFilters({ ...filters, jobId: e.target.value })}>
              <option value="">All jobs</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          )}
          <select className="input" value={filters.tier} onChange={(e) => setFilters({ ...filters, tier: e.target.value })}>
            <option value="">Any recommendation</option>
            {TIER_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={filters.meetsRequired}
            onChange={(e) => setFilters({ ...filters, meetsRequired: e.target.value })}
          >
            <option value="">Mandatory requirements: any</option>
            <option value="true">Meets all mandatory requirements</option>
            <option value="false">Missing mandatory requirements</option>
          </select>
          <select
            className="input"
            value={filters.processingStatus}
            onChange={(e) => setFilters({ ...filters, processingStatus: e.target.value })}
          >
            <option value="">Any processing status</option>
            {PROCESSING_STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <input
            className="input"
            type="number"
            placeholder="Min score (0-100)"
            value={filters.minScore}
            onChange={(e) => setFilters({ ...filters, minScore: e.target.value })}
          />
          <input
            className="input"
            type="number"
            placeholder="Max score (0-100)"
            value={filters.maxScore}
            onChange={(e) => setFilters({ ...filters, maxScore: e.target.value })}
          />
          <input
            className="input"
            type="number"
            placeholder="Min years experience"
            value={filters.minExperience}
            onChange={(e) => setFilters({ ...filters, minExperience: e.target.value })}
          />
          <input
            className="input"
            placeholder="Skill contains..."
            value={filters.skills}
            onChange={(e) => setFilters({ ...filters, skills: e.target.value })}
          />
          <input
            className="input"
            placeholder="Education contains..."
            value={filters.education}
            onChange={(e) => setFilters({ ...filters, education: e.target.value })}
          />
          <input
            className="input"
            placeholder="Location contains..."
            value={filters.location}
            onChange={(e) => setFilters({ ...filters, location: e.target.value })}
          />
          <input
            className="input"
            placeholder="Work authorization contains..."
            value={filters.workAuthorization}
            onChange={(e) => setFilters({ ...filters, workAuthorization: e.target.value })}
          />
        </div>

        {activeFilters.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-2">
            {activeFilters.map((f) => (
              <span key={f.key} className="text-xs bg-slate-100 rounded-full px-3 py-1 flex items-center gap-1.5">
                {f.label}
                <button type="button" className="font-bold" onClick={() => setFilters({ ...filters, [f.key]: "" })}>
                  ×
                </button>
              </span>
            ))}
            <button type="button" className="text-xs text-electric font-semibold" onClick={() => setFilters({ ...emptyFilters, jobId: fixedJobId || "" })}>
              Clear all filters
            </button>
          </div>
        )}
      </div>

      <div className="mt-4 space-y-3">
        <SuccessBanner message={success} onDismiss={() => setSuccess("")} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>

      {duplicates.length > 0 && (
        <div className="card mt-4 space-y-2 border-amber-200 bg-amber-50">
          <h2 className="font-bold text-sm">Duplicate candidates detected</h2>
          {duplicates.map((d) => (
            <div key={d.filename} className="flex items-center justify-between text-sm gap-3">
              <span>
                &quot;{d.filename}&quot; matches existing candidate{" "}
                <Link href={`/dashboard/candidates/${d.existing_candidate_id}`} className="text-electric font-semibold">
                  {d.existing_candidate_name}
                </Link>
              </span>
              <div className="flex gap-2 shrink-0">
                <button type="button" className="btn-secondary text-xs px-3 py-1.5" onClick={() => setDuplicates((prev) => prev.filter((x) => x.filename !== d.filename))}>
                  Use existing
                </button>
                <button type="button" className="btn-primary text-xs px-3 py-1.5" onClick={() => uploadDuplicateAsNew(d)}>
                  Upload as new
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected.size > 0 && (
        <div className="card mt-4 flex flex-wrap items-center gap-3 bg-electric/5 border-electric/20">
          <span className="text-sm font-semibold">{selected.size} selected</span>
          <button type="button" className="btn-secondary text-sm" disabled={bulkBusy} onClick={() => bulkShortlist(true)}>
            Add to shortlist
          </button>
          <button type="button" className="btn-secondary text-sm" disabled={bulkBusy} onClick={() => bulkShortlist(false)}>
            Remove from shortlist
          </button>
          <button
            type="button"
            className="btn-secondary text-sm"
            disabled={bulkBusy || selected.size < 2 || selected.size > 10}
            onClick={compareSelected}
            title={selected.size < 2 || selected.size > 10 ? "Select 2-10 candidates to compare" : ""}
          >
            Compare selected
          </button>
          <button type="button" className="btn-secondary text-sm" disabled={bulkBusy} onClick={() => router.push(`/dashboard/outreach?ids=${Array.from(selected).join(",")}`)}>
            Email selected
          </button>
          <button type="button" className="btn-secondary text-sm" disabled={bulkBusy} onClick={exportSelected}>
            Export selected
          </button>
          <button type="button" className="btn-secondary text-sm" disabled={bulkBusy} onClick={bulkRetry}>
            Retry failed processing
          </button>
          <button type="button" className="text-sm text-slate-500" onClick={() => setSelected(new Set())}>
            Clear selection
          </button>
        </div>
      )}

      {batchId && (
        <div className="mt-6">
          <ProcessingProgress
            batchId={batchId}
            onDone={(batch) => {
              setSuccess(`Processing finished: ${batch.completed_count} completed, ${batch.failed_count} failed.`);
              load();
            }}
          />
          <button type="button" className="text-sm text-electric font-semibold mt-2" onClick={() => setBatchId(null)}>
            Dismiss
          </button>
        </div>
      )}

      {!batchId && (
        <form onSubmit={upload} className="card mt-6 space-y-3">
          <div>
            <label className="label">Upload CVs (select multiple files, up to 300)</label>
            <input
              type="file"
              accept=".pdf,.docx,.txt"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
            {files.length > 0 && <p className="text-xs text-slate-500 mt-2">{files.length} file(s) selected</p>}
          </div>
          {!fixedJobId && (
            <div>
              <label className="label">Score against job (optional)</label>
              <select className="input max-w-sm" value={uploadJobId} onChange={(e) => setUploadJobId(e.target.value)}>
                <option value="">Don&apos;t score yet</option>
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title}
                  </option>
                ))}
              </select>
            </div>
          )}
          <button className="btn-primary" disabled={files.length === 0 || uploading}>
            {uploading ? `Uploading ${files.length} CV(s)...` : `Upload ${files.length ? `(${files.length})` : ""}`}
          </button>
        </form>
      )}

      <div className="card mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="pb-2">
                <input
                  type="checkbox"
                  checked={rows.length > 0 && selected.size === rows.length}
                  onChange={toggleSelectAll}
                  aria-label="Select all filtered"
                />
              </th>
              <th className="pb-2">#</th>
              <th className="pb-2 cursor-pointer select-none" onClick={() => toggleSort("name")}>
                Candidate{sort === "name" ? (order === "asc" ? " ▲" : " ▼") : ""}
              </th>
              <th className="pb-2 cursor-pointer select-none" onClick={() => toggleSort("score")}>
                Match{sort === "score" ? (order === "asc" ? " ▲" : " ▼") : ""}
              </th>
              <th className="pb-2">Recommendation</th>
              <th className="pb-2 cursor-pointer select-none" onClick={() => toggleSort("experience_years")}>
                Experience{sort === "experience_years" ? (order === "asc" ? " ▲" : " ▼") : ""}
              </th>
              <th className="pb-2">Top Skills</th>
              <th className="pb-2">Missing Requirements</th>
              <th className="pb-2">Status</th>
              <th className="pb-2"></th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={10} className="py-6 text-slate-500 text-center">
                  No candidates yet. Upload CVs to get started.
                </td>
              </tr>
            )}
            {rows.map((r, i) => (
              <tr key={r.id} className="border-b border-slate-50">
                <td className="py-3">
                  <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSelected(r.id)} aria-label={`Select ${r.name}`} />
                </td>
                <td className="py-3 text-slate-400">{sort === "score" && order === "desc" ? `#${i + 1}` : ""}</td>
                <td className="py-3">
                  <div className="font-semibold">{r.name}</div>
                  <div className="text-xs text-slate-400">{r.current_role}</div>
                </td>
                <td className="py-3">{r.score ? `${r.score}/100` : "—"}</td>
                <td className="py-3">
                  {r.score_status ? (
                    <span className={`text-xs rounded-full px-2 py-0.5 ${tierBadgeClass(r.score_status)}`}>{r.score_status}</span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="py-3">{r.experience_years ? `${r.experience_years} yrs` : "—"}</td>
                <td className="py-3 max-w-[180px] truncate" title={r.skills}>
                  {topSkills(r.skills)}
                </td>
                <td className="py-3 max-w-[200px] truncate" title={missingRequirements(r.requirement_results)}>
                  {missingRequirements(r.requirement_results)}
                </td>
                <td className="py-3">
                  {r.processing_status === "Failed" ? (
                    <span className="text-red-600">
                      Failed —{" "}
                      <button type="button" className="font-semibold underline" onClick={() => retryOne(r.id)}>
                        Retry
                      </button>
                    </span>
                  ) : (
                    r.status
                  )}
                </td>
                <td className="py-3 space-x-3">
                  <Link href={`/dashboard/candidates/${r.id}`} className="text-electric font-semibold">
                    View
                  </Link>
                  <button type="button" className="text-red-600 font-semibold" onClick={() => removeCandidate(r)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
