"use client";

import { useEffect, useRef, useState } from "react";
import { getProcessingBatch, retryProcessingBatch, ProcessingBatch } from "@/lib/upload";

const TERMINAL = new Set(["Completed", "Completed with errors", "Failed"]);

const STATUS_ICON: Record<string, string> = {
  Uploaded: "○",
  Queued: "○",
  Extracting: "…",
  Analyzing: "…",
  Scoring: "…",
  Completed: "✓",
  "Needs review": "⚠",
  Failed: "✗",
};

export default function ProcessingProgress({
  batchId,
  onDone,
}: {
  batchId: string;
  onDone?: (batch: ProcessingBatch) => void;
}) {
  const [batch, setBatch] = useState<ProcessingBatch | null>(null);
  const [retrying, setRetrying] = useState(false);
  const startedAt = useRef(Date.now());
  const doneFired = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      try {
        const result = await getProcessingBatch(batchId);
        if (cancelled) return;
        setBatch(result);
        if (TERMINAL.has(result.status)) {
          if (!doneFired.current) {
            doneFired.current = true;
            onDone?.(result);
          }
          return;
        }
        timer = setTimeout(poll, 2000);
      } catch {
        timer = setTimeout(poll, 3000);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId]);

  async function retryFailed() {
    setRetrying(true);
    try {
      await retryProcessingBatch(batchId);
      doneFired.current = false;
      const refreshed = await getProcessingBatch(batchId);
      setBatch(refreshed);
    } finally {
      setRetrying(false);
    }
  }

  if (!batch) return <p className="text-sm text-slate-500">Starting…</p>;

  const done = batch.completed_count + batch.failed_count;
  const pct = batch.total_count > 0 ? Math.round((done / batch.total_count) * 100) : 0;
  const processing = batch.candidates.filter(
    (c) => !["Completed", "Needs review", "Failed"].includes(c.processing_status)
  ).length;
  const successful = batch.candidates.filter((c) => ["Completed", "Needs review"].includes(c.processing_status)).length;
  const isTerminal = TERMINAL.has(batch.status);

  const elapsedSec = (Date.now() - startedAt.current) / 1000;
  const etaLabel =
    !isTerminal && done >= 5 && done < batch.total_count
      ? formatEta(((elapsedSec / done) * (batch.total_count - done)))
      : null;

  return (
    <div className="card space-y-4">
      <div>
        <h2 className="font-bold">{isTerminal ? "Processing complete" : "Analyzing candidates"}</h2>
        <p className="text-sm text-slate-500 mt-1">
          {isTerminal
            ? `${batch.status}.`
            : etaLabel
              ? `Estimated ${etaLabel} remaining. You can safely leave this page — processing continues in the background.`
              : "Calculating time remaining… You can safely leave this page — processing continues in the background."}
        </p>
      </div>

      <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
        <div className="bg-electric h-3 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
        <span className="font-semibold">
          {done} / {batch.total_count} completed ({pct}%)
        </span>
        <span className="text-green-700">{successful} successful</span>
        <span className="text-slate-500">{processing} processing</span>
        {batch.failed_count > 0 && <span className="text-red-600">{batch.failed_count} failed</span>}
      </div>

      {isTerminal && batch.failed_count > 0 && (
        <button type="button" className="btn-secondary text-sm" onClick={retryFailed} disabled={retrying}>
          {retrying ? "Retrying…" : `Retry ${batch.failed_count} failed CV(s)`}
        </button>
      )}

      <div className="max-h-64 overflow-y-auto border-t border-slate-100 pt-3 space-y-1.5 text-sm">
        {batch.candidates.map((c) => (
          <div key={c.id} className="flex items-center justify-between gap-3">
            <span className="truncate">{c.filename}</span>
            <span
              className={
                c.processing_status === "Failed"
                  ? "text-red-600 font-semibold"
                  : c.processing_status === "Completed"
                    ? "text-green-600 font-semibold"
                    : "text-slate-500"
              }
            >
              {STATUS_ICON[c.processing_status] || "○"} {c.processing_status}
              {c.processing_error ? ` — ${c.processing_error}` : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatEta(seconds: number): string {
  if (seconds < 60) return `${Math.max(1, Math.round(seconds))}s`;
  const minutes = Math.round(seconds / 60);
  return `${minutes} min`;
}
