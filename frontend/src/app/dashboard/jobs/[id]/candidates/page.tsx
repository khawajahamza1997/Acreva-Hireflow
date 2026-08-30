"use client";

import { useParams } from "next/navigation";
import CandidatesView from "@/components/CandidatesView";

export default function JobCandidatesPage() {
  const params = useParams<{ id: string }>();
  return <CandidatesView fixedJobId={params.id} />;
}
