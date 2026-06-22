import Link from "next/link";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <header className="flex items-center justify-between px-8 py-5 max-w-6xl mx-auto">
        <div className="text-xl font-extrabold">
          Acreva <span className="text-electric">HireFlow</span>
        </div>
        <div className="flex gap-3">
          <Link href="/login" className="btn-secondary text-sm">
            Log in
          </Link>
          <Link href="/signup" className="btn-primary text-sm">
            Start free trial
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-8 py-16 grid lg:grid-cols-2 gap-12 items-center">
        <div>
          <div className="inline-block bg-orange/10 text-orange text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full mb-4">
            14-day free trial · $39/mo after
          </div>
          <h1 className="text-4xl lg:text-5xl font-extrabold leading-tight tracking-tight">
            AI-assisted recruitment from CV to interview
          </h1>
          <p className="mt-5 text-lg text-slate-600 leading-relaxed">
            Upload CVs, score against your job description, auto-shortlist top candidates,
            send outreach emails, and track your pipeline — without enterprise complexity.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/signup" className="btn-primary">
              Start free trial
            </Link>
            <Link href="/login" className="btn-secondary">
              View demo workspace
            </Link>
          </div>
          <p className="mt-4 text-xs text-slate-500">
            AI assists screening only. Final hiring decisions stay with your team.
          </p>
        </div>

        <div className="card bg-navy text-white border-0 p-0 overflow-hidden">
          <div className="p-6 border-b border-white/10">
            <div className="text-sm text-slate-300">Recruitment dashboard preview</div>
          </div>
          <div className="p-6 grid grid-cols-2 gap-4">
            {[
              ["Total candidates", "24"],
              ["Shortlisted", "6"],
              ["Scored today", "12"],
              ["Interviews", "3"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-white/5 p-4">
                <div className="text-2xl font-bold text-electric">{value}</div>
                <div className="text-xs text-slate-400 mt-1">{label}</div>
              </div>
            ))}
          </div>
          <div className="px-6 pb-6 text-sm text-slate-400">
            Pipeline: New → Scored → Shortlisted → Contacted → Interview
          </div>
        </div>
      </main>

      <section className="bg-white border-y border-slate-200 py-16">
        <div className="max-w-6xl mx-auto px-8 grid md:grid-cols-3 gap-8">
          {[
            ["Upload & parse CVs", "PDF, Word, or text — AI extracts candidate profiles automatically."],
            ["Score & shortlist", "Weighted AI scoring against your job description. Top N auto-shortlisted."],
            ["Email & track", "Branded outreach templates, audit log, and full pipeline visibility."],
          ].map(([title, desc]) => (
            <div key={title} className="card">
              <h3 className="font-bold text-lg mb-2">{title}</h3>
              <p className="text-sm text-slate-600 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-16 max-w-3xl mx-auto px-8 text-center">
        <h2 className="text-3xl font-extrabold">Simple pricing</h2>
        <div className="card mt-8 text-left">
          <div className="text-sm font-bold text-electric uppercase">Starter</div>
          <div className="text-4xl font-extrabold mt-2">
            $39<span className="text-lg text-slate-500 font-semibold">/month</span>
          </div>
          <ul className="mt-6 space-y-2 text-sm text-slate-600">
            <li>✓ 14-day free trial</li>
            <li>✓ Unlimited jobs</li>
            <li>✓ AI CV parsing & scoring</li>
            <li>✓ Outreach emails via Resend</li>
            <li>✓ Team accounts (owner + recruiter)</li>
            <li>✓ Audit log & pipeline dashboard</li>
          </ul>
          <Link href="/signup" className="btn-primary inline-block mt-8">
            Start free trial
          </Link>
        </div>
      </section>

      <footer className="border-t border-slate-200 py-8 text-center text-sm text-slate-500">
        <div className="flex justify-center gap-6 mb-3">
          <Link href="/legal/terms" className="hover:text-electric">
            Terms
          </Link>
          <Link href="/legal/privacy" className="hover:text-electric">
            Privacy
          </Link>
          <a href="mailto:support@acreva.com" className="hover:text-electric">
            support@acreva.com
          </a>
        </div>
        © {new Date().getFullYear()} Acreva HireFlow
      </footer>
    </div>
  );
}
