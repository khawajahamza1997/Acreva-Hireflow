"use client";

import { useParams } from "next/navigation";
import AuditLogView from "@/components/AuditLogView";

export default function JobActivityPage() {
  const params = useParams<{ id: string }>();
  return <AuditLogView fixedJobId={params.id} />;
}
