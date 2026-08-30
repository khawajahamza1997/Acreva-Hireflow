"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Job = { id: string; title: string };
type Candidate = { id: string; name: string };

type SuggestedAction = {
  type: "show_candidates" | "add_to_shortlist" | "remove_from_shortlist" | "compare" | "none";
  candidate_ids: string[];
  requires_confirmation: boolean;
};

type AskResponse = {
  answer: string;
  cited_candidate_ids: string[];
  suggested_action: SuggestedAction;
};

type Message = {
  role: "user" | "assistant";
  text: string;
  citedIds?: string[];
  action?: SuggestedAction;
  resolved?: boolean;
};

const ACTION_LABEL: Record<string, string> = {
  add_to_shortlist: "add these candidates to the shortlist",
  remove_from_shortlist: "remove these candidates from the shortlist",
};

export default function AskHireFlowView({ fixedJobId }: { fixedJobId?: string }) {
  const router = useRouter();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobId, setJobId] = useState(fixedJobId || "");
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (fixedJobId) return;
    api<Job[]>("/api/v1/jobs").then((j) => {
      setJobs(j);
      if (j[0]) setJobId(j[0].id);
    });
  }, [fixedJobId]);

  useEffect(() => {
    if (!jobId) return;
    api<Candidate[]>(`/api/v1/candidates?job_id=${jobId}`).then(setCandidates).catch(() => setCandidates([]));
    setMessages([]);
  }, [jobId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function nameFor(id: string): string {
    return candidates.find((c) => c.id === id)?.name || "Candidate";
  }

  async function ask() {
    if (!question.trim() || !jobId) return;
    const q = question.trim();
    setMessages((prev) => [...prev, { role: "user", text: q }]);
    setQuestion("");
    setAsking(true);
    setError("");
    try {
      const res = await api<AskResponse>("/api/v1/ask", {
        method: "POST",
        body: JSON.stringify({ job_id: jobId, question: q }),
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, citedIds: res.cited_candidate_ids, action: res.suggested_action },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask HireFlow could not answer that.");
    } finally {
      setAsking(false);
    }
  }

  async function confirmAction(index: number) {
    const msg = messages[index];
    if (!msg.action) return;
    try {
      const shortlisted = msg.action.type === "add_to_shortlist";
      const res = await api<{ message: string }>("/api/v1/candidates/bulk-shortlist", {
        method: "POST",
        body: JSON.stringify({ candidate_ids: msg.action.candidate_ids, shortlisted }),
      });
      setMessages((prev) => {
        const next = [...prev];
        next[index] = { ...next[index], resolved: true };
        return [...next, { role: "assistant", text: res.message }];
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    }
  }

  function cancelAction(index: number) {
    setMessages((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], resolved: true };
      return next;
    });
  }

  return (
    <div className="max-w-3xl">
      {!fixedJobId && (
        <>
          <h1 className="text-2xl font-extrabold">Ask HireFlow</h1>
          <p className="text-sm text-slate-500 mt-1">
            Ask questions about this job&apos;s candidate pool. Answers are grounded only in the uploaded CVs and scoring
            data — HireFlow will say so when something isn&apos;t established, rather than guess.
          </p>
        </>
      )}

      {!fixedJobId && (
        <select className="input mt-4 max-w-sm" value={jobId} onChange={(e) => setJobId(e.target.value)}>
          {jobs.map((j) => (
            <option key={j.id} value={j.id}>
              {j.title}
            </option>
          ))}
        </select>
      )}

      {error && <p className="text-sm text-red-600 mt-3">{error}</p>}

      <div className="card mt-4 min-h-[300px] max-h-[55vh] overflow-y-auto space-y-4">
        {messages.length === 0 && (
          <p className="text-sm text-slate-500">
            Try: &quot;Which candidates have 5+ years Python?&quot;, &quot;Why was the top candidate ranked highest?&quot;,
            or &quot;Add the top 5 to my shortlist.&quot;
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <div
              className={`inline-block rounded-xl px-4 py-2 text-sm max-w-[85%] ${
                m.role === "user" ? "bg-electric text-white" : "bg-slate-100 text-navy"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.text}</p>
              {m.citedIds && m.citedIds.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {m.citedIds.map((id) => (
                    <Link key={id} href={`/dashboard/candidates/${id}`} className="text-xs text-electric font-semibold underline">
                      {nameFor(id)}
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {m.action && m.action.type !== "none" && !m.resolved && (
              <div className="mt-2">
                {m.action.requires_confirmation ? (
                  <div className="inline-block bg-amber-50 border border-amber-200 rounded-xl px-4 py-2 text-sm text-left">
                    <p>
                      You asked me to {ACTION_LABEL[m.action.type] || "make a change"} ({m.action.candidate_ids.length} candidate(s)).
                    </p>
                    <div className="mt-2 flex gap-2">
                      <button type="button" className="btn-primary text-xs px-3 py-1.5" onClick={() => confirmAction(i)}>
                        Confirm
                      </button>
                      <button type="button" className="btn-secondary text-xs px-3 py-1.5" onClick={() => cancelAction(i)}>
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : m.action.type === "compare" && m.action.candidate_ids.length >= 2 ? (
                  <button
                    type="button"
                    className="text-xs text-electric font-semibold underline"
                    onClick={() => router.push(`/dashboard/candidates/compare?ids=${m.action!.candidate_ids.join(",")}`)}
                  >
                    View comparison →
                  </button>
                ) : m.action.type === "show_candidates" ? (
                  <button
                    type="button"
                    className="text-xs text-electric font-semibold underline"
                    onClick={() => router.push(fixedJobId ? `/dashboard/jobs/${fixedJobId}/candidates` : `/dashboard/candidates`)}
                  >
                    View candidates →
                  </button>
                ) : null}
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        className="mt-4 flex gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          ask();
        }}
      >
        <input
          className="input"
          placeholder="Ask about this job's candidates..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={asking || !jobId}
        />
        <button className="btn-primary" disabled={asking || !question.trim() || !jobId}>
          {asking ? "Asking..." : "Ask"}
        </button>
      </form>
    </div>
  );
}
