import { api } from "./api";

export type DuplicateCandidate = {
  filename: string;
  existing_candidate_id: string;
  existing_candidate_name: string;
};

export type BatchUploadResult = {
  batch_id: string | null;
  total: number;
  rejected: Array<{ filename: string; error: string }>;
  duplicates: DuplicateCandidate[];
  message: string;
};

export type ProcessingCandidate = {
  id: string;
  name: string;
  filename: string;
  processing_status: string;
  processing_error?: string;
};

export type ProcessingBatch = {
  id: string;
  status: "Uploading" | "Queued" | "Processing" | "Completed" | "Completed with errors" | "Failed";
  total_count: number;
  completed_count: number;
  failed_count: number;
  created_at: string;
  candidates: ProcessingCandidate[];
};

/** Upload multiple CV files in one request (PDF, DOCX, TXT) — processed in the background.
 * Files whose content exactly matches an existing candidate come back in `duplicates` instead
 * of being processed; re-call with the same filenames in `bypassDuplicateFilenames` to force them through. */
export async function uploadCvBatch(
  files: File[],
  jobId?: string,
  bypassDuplicateFilenames?: string[]
): Promise<BatchUploadResult> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  if (jobId) form.append("job_id", jobId);
  if (bypassDuplicateFilenames && bypassDuplicateFilenames.length > 0) {
    form.append("bypass_duplicate_check", bypassDuplicateFilenames.join(","));
  }
  return api<BatchUploadResult>("/api/v1/candidates/upload-batch", { method: "POST", body: form });
}

export async function getProcessingBatch(batchId: string): Promise<ProcessingBatch> {
  return api<ProcessingBatch>(`/api/v1/processing-batches/${batchId}`);
}

export async function retryProcessingBatch(batchId: string, candidateIds?: string[]): Promise<{ message: string }> {
  return api(`/api/v1/processing-batches/${batchId}/retry`, {
    method: "POST",
    body: JSON.stringify({ candidate_ids: candidateIds || null }),
  });
}

export async function retryCandidateProcessing(candidateId: string): Promise<{ message: string }> {
  return api(`/api/v1/candidates/${candidateId}/retry-processing`, { method: "POST" });
}

/** Force a fresh scoring pass regardless of current status — may consume additional AI credits. */
export async function reanalyzeCandidate(candidateId: string): Promise<{ batch_id: string; message: string }> {
  return api(`/api/v1/candidates/${candidateId}/reanalyze`, { method: "POST" });
}

/** Upload a call recording / voice note for a candidate — transcribes and extracts call data. */
export async function uploadCallRecording(candidateId: string, file: File, consent: boolean) {
  const form = new FormData();
  form.append("file", file);
  form.append("consent", String(consent));
  return api(`/api/v1/candidates/${candidateId}/call-recording`, { method: "POST", body: form });
}
