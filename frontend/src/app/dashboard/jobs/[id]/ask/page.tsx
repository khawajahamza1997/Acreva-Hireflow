"use client";

import { useParams } from "next/navigation";
import AskHireFlowView from "@/components/AskHireFlowView";

export default function JobAskPage() {
  const params = useParams<{ id: string }>();
  return <AskHireFlowView fixedJobId={params.id} />;
}
