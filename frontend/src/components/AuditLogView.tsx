"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Log = {
  id: string;
  action: string;
  user_email: string;
  entity_type: string;
  created_at: string;
  details: Record<string, unknown>;
};

function describe(log: Log): string {
  const d = log.details || {};
  switch (log.action) {
    case "candidate_scored":
      return `AI score: ${d.score ?? "?"} (requirements v${d.requirements_version ?? 1}, ${d.model || "model"})`;
    case "candidate_processed":
      return `CV processed — status: ${d.status ?? "Completed"}`;
    case "candidate_shortlisted":
      return d.bulk ? "Recruiter added candidate to shortlist (bulk)" : "Recruiter added candidate to shortlist";
    case "candidate_unshortlisted":
      return d.bulk ? "Recruiter removed candidate from shortlist (bulk)" : "Recruiter removed candidate from shortlist";
    case "candidate_updated":
      return `Recruiter updated: ${Object.keys(d).join(", ") || "candidate"}`;
    case "candidates_compared":
      return `Recruiter compared ${(d.candidate_ids as string[] | undefined)?.length ?? "multiple"} candidates`;
    case "ask_hireflow_query":
      return `Ask HireFlow: "${d.question ?? ""}"`;
    case "job_requirements_versioned":
      return `Job requirements updated to v${d.new_version}`;
    case "email_sent":
      return `Email sent to ${d.to ?? "candidate"}${d.bulk ? " (bulk)" : ""}`;
    case "email_preview":
      return "Email previewed (demo mode — not sent)";
    case "candidates_exported":
      return `Exported ${d.count ?? ""} candidate(s) to CSV`;
    case "batch_upload_started":
      return `Batch upload started (${d.total ?? "?"} CV(s), ${d.rejected ?? 0} rejected, ${d.duplicates ?? 0} duplicates skipped)`;
    case "scoring_batch_started":
      return `Scoring started for ${d.total ?? "?"} candidate(s)`;
    case "candidate_reanalyze_requested":
      return "Recruiter requested re-analysis";
    case "possible_duplicate_email":
      return `Possible duplicate — email matches: ${((d.matches as string[] | undefined) || []).join(", ")}`;
    default:
      return log.action.replace(/_/g, " ");
  }
}

export default function AuditLogView({ fixedJobId }: { fixedJobId?: string }) {
  const [logs, setLogs] = useState<Log[]>([]);

  useEffect(() => {
    const url = fixedJobId ? `/api/v1/audit-logs?job_id=${fixedJobId}` : "/api/v1/audit-logs";
    api<Log[]>(url).then(setLogs);
  }, [fixedJobId]);

  return (
    <div>
      {!fixedJobId && (
        <>
          <h1 className="text-2xl font-extrabold">Audit log</h1>
          <p className="text-sm text-slate-500 mt-1">Every AI screening result and recruiter action, traceable.</p>
        </>
      )}
      <div className="card mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              <th className="pb-2">When</th>
              <th className="pb-2">User</th>
              <th className="pb-2">Event</th>
              <th className="pb-2">Entity</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-slate-500 text-center">
                  No activity yet.
                </td>
              </tr>
            )}
            {logs.map((l) => (
              <tr key={l.id} className="border-b border-slate-50">
                <td className="py-3 whitespace-nowrap">{new Date(l.created_at).toLocaleString()}</td>
                <td className="py-3">{l.user_email}</td>
                <td className="py-3 font-semibold">{describe(l)}</td>
                <td className="py-3 text-slate-400">{l.entity_type}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
