"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { tierBadgeClass } from "@/lib/tier";

type Candidate = {
  id: string;
  name: string;
  score?: number;
  score_status?: string;
  score_breakdown?: Record<string, number>;
  meets_required?: boolean | null;
};

type CompareResult = { candidates: Candidate[]; summary: string };

const CATEGORY_LABELS: Record<string, string> = {
  required_skills: "Required skills",
  preferred_skills: "Preferred skills",
  experience: "Experience",
  education: "Education",
  certifications: "Certifications",
  industry_experience: "Industry experience",
};

export default function ComparePage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <CompareContent />
    </Suspense>
  );
}

function CompareContent() {
  const params = useSearchParams();
  const ids = (params.get("ids") || "").split(",").filter(Boolean);
  const [result, setResult] = useState<CompareResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (ids.length < 2) return;
    api<CompareResult>("/api/v1/candidates/compare", {
      method: "POST",
      body: JSON.stringify({ candidate_ids: ids }),
    })
      .then(setResult)
      .catch((err) => setError(err instanceof Error ? err.message : "Comparison failed."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const categories = Object.keys(
    (result?.candidates[0]?.score_breakdown as Record<string, number>) || {}
  );

  return (
    <div>
      <Link href="/dashboard/candidates" className="text-sm text-electric font-semibold">
        ← Back to candidates
      </Link>
      <h1 className="text-2xl font-extrabold mt-2">Compare candidates</h1>
      <p className="text-sm text-slate-500 mt-1">
        AI comparison — based only on job-relevant scoring data. Final selection is yours.
      </p>

      {error && <p className="text-sm text-red-600 mt-4">{error}</p>}
      {ids.length < 2 && <p className="text-sm text-slate-500 mt-4">Select 2-10 candidates from the candidates page first.</p>}

      {result && (
        <>
          <div className="card mt-6 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-slate-500 border-b">
                  <th className="pb-2">Criterion</th>
                  {result.candidates.map((c) => (
                    <th key={c.id} className="pb-2">
                      <Link href={`/dashboard/candidates/${c.id}`} className="text-electric">
                        {c.name}
                      </Link>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-slate-50">
                  <td className="py-2 font-semibold">Overall</td>
                  {result.candidates.map((c) => (
                    <td key={c.id} className="py-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{c.score ?? "—"}</span>
                        <span className={`text-xs rounded-full px-2 py-0.5 ${tierBadgeClass(c.score_status)}`}>{c.score_status}</span>
                      </div>
                    </td>
                  ))}
                </tr>
                {categories.map((cat) => (
                  <tr key={cat} className="border-b border-slate-50">
                    <td className="py-2">{CATEGORY_LABELS[cat] || cat}</td>
                    {result.candidates.map((c) => (
                      <td key={c.id} className="py-2">
                        {Math.round((c.score_breakdown || {})[cat] ?? 0)}/100
                      </td>
                    ))}
                  </tr>
                ))}
                <tr>
                  <td className="py-2">Meets all mandatory requirements</td>
                  {result.candidates.map((c) => (
                    <td key={c.id} className="py-2">
                      {c.meets_required ? <span className="text-green-700">✓ Yes</span> : <span className="text-amber-600">⚠ Not confirmed</span>}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          <div className="card mt-6">
            <h2 className="font-bold mb-2">AI comparison summary</h2>
            <p className="text-sm text-slate-700 whitespace-pre-wrap">{result.summary}</p>
          </div>
        </>
      )}
    </div>
  );
}
