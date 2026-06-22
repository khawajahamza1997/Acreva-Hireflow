import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { clearTokens } from "@/lib/api";

const links = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/dashboard/onboarding", label: "Onboarding" },
  { href: "/dashboard/jobs", label: "Jobs" },
  { href: "/dashboard/candidates", label: "Candidates" },
  { href: "/dashboard/scoring", label: "Scoring" },
  { href: "/dashboard/pipeline", label: "Pipeline" },
  { href: "/dashboard/shortlist", label: "Shortlist" },
  { href: "/dashboard/outreach", label: "Outreach" },
  { href: "/dashboard/audit", label: "Audit Log" },
  { href: "/dashboard/team", label: "Team" },
  { href: "/dashboard/settings", label: "Settings" },
  { href: "/dashboard/billing", label: "Billing" },
];

export default function DashboardNav() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="w-64 shrink-0 bg-navy text-white min-h-screen p-5 flex flex-col">
      <div className="mb-8">
        <div className="text-xl font-extrabold tracking-tight">
          Acreva <span className="text-electric">HireFlow</span>
        </div>
        <div className="text-[10px] uppercase tracking-widest text-slate-400 mt-1">
          AI Recruitment Assistant
        </div>
      </div>
      <nav className="flex flex-col gap-1 flex-1">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`rounded-lg px-3 py-2 text-sm transition ${
              pathname === link.href
                ? "bg-electric/20 text-white font-semibold"
                : "text-slate-300 hover:bg-white/5"
            }`}
          >
            {link.label}
          </Link>
        ))}
      </nav>
      <button
        onClick={() => {
          clearTokens();
          router.push("/login");
        }}
        className="mt-4 text-sm text-slate-400 hover:text-white text-left"
      >
        Sign out
      </button>
    </aside>
  );
}
