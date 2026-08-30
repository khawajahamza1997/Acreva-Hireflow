"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import OutreachView from "@/components/OutreachView";

export default function OutreachPage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <OutreachPageContent />
    </Suspense>
  );
}

function OutreachPageContent() {
  const params = useSearchParams();
  const presetIds = (params.get("ids") || "").split(",").filter(Boolean);
  return <OutreachView presetIds={presetIds} />;
}
