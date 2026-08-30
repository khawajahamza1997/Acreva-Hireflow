"use client";

import { useParams } from "next/navigation";
import OutreachView from "@/components/OutreachView";

export default function JobEmailsPage() {
  const params = useParams<{ id: string }>();
  return <OutreachView fixedJobId={params.id} />;
}
