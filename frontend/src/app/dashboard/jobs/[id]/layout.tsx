"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Job = { id: string; title: string; requirements_version?: number };

const TABS = [
  { suffix: "", label: "Overview" },
  { suffix: "/candidates", label: "Candidates" },
  { suffix: "/shortlist", label: "Shortlist" },
  { suffix: "/compare", label: "Compare" },
  { suffix: "/ask", label: "Ask HireFlow" },
  { suffix: "/emails", label: "Emails" },
  { suffix: "/activity", label: "Activity" },
];

export default function JobWorkspaceLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const params = useParams<{ id: string }>();
  const [job, setJob] = useState<Job | null>(null);

  useEffect(() => {
    api<Job>(`/api/v1/jobs/${params.id}`)
      .then(setJob)
      .catch(() => setJob(null));
  }, [params.id]);

  const base = `/dashboard/jobs/${params.id}`;

  return (
    <div>
      <Link href="/dashboard/jobs" className="text-sm text-electric font-semibold">
        ← All jobs
      </Link>
      <div className="flex items-center gap-3 mt-2">
        <h1 className="text-2xl font-extrabold">{job?.title || "Loading…"}</h1>
        {job && (
          <span className="text-xs font-normal bg-slate-100 text-slate-500 rounded-full px-2 py-0.5">
            Requirements v{job.requirements_version ?? 1}
          </span>
        )}
      </div>

      <nav className="flex flex-wrap gap-1 mt-4 border-b border-slate-200">
        {TABS.map((tab) => {
          const href = `${base}${tab.suffix}`;
          const active = pathname === href || (tab.suffix === "/compare" && pathname.startsWith(`${base}/compare`));
          return (
            <Link
              key={tab.suffix}
              href={href}
              className={`px-4 py-2 text-sm font-semibold rounded-t-lg ${
                active ? "bg-white border border-b-0 border-slate-200 text-electric" : "text-slate-500 hover:text-navy"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>

      <div className="pt-6">{children}</div>
    </div>
  );
}
