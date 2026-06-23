import { api } from "./api";

export type BatchUploadResult = {
  uploaded: number;
  failed: number;
  message: string;
  candidates: Array<{ id: string; name: string }>;
  errors?: Array<{ filename: string; error: string }>;
};

/** Upload multiple CV files in one request (PDF, DOCX, TXT). */
export async function uploadCvBatch(files: File[], jobId?: string): Promise<BatchUploadResult> {
  const form = new FormData();
  files.forEach((file) => form.append("files", file));
  if (jobId) form.append("job_id", jobId);
  return api<BatchUploadResult>("/api/v1/candidates/upload-batch", { method: "POST", body: form });
}
