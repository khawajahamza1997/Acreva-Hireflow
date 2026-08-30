"use client";

import { useParams } from "next/navigation";
import ShortlistView from "@/components/ShortlistView";

export default function JobShortlistPage() {
  const params = useParams<{ id: string }>();
  return <ShortlistView fixedJobId={params.id} />;
}
