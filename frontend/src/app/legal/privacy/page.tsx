import Link from "next/link";

export default function PrivacyPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <Link href="/" className="text-electric text-sm font-semibold">
        ← Back
      </Link>
      <h1 className="text-3xl font-extrabold mt-6">Privacy Policy</h1>
      <p className="text-sm text-slate-500 mt-2">Last updated: June 2026</p>
      <div className="prose prose-sm mt-8 space-y-4 text-slate-700">
        <p>
          We collect account information (name, email, organization), candidate data you upload (CV files
          and extracted fields), and usage logs required to operate the service.
        </p>
        <p>
          CV files are stored securely and processed by AI services to provide parsing and scoring.
          We do not sell candidate data to third parties.
        </p>
        <p>
          You may request deletion of your organization data by contacting{" "}
          <a href="mailto:support@acreva.com" className="text-electric">
            support@acreva.com
          </a>
          .
        </p>
        <p>
          We use subprocessors including cloud hosting, OpenAI (AI processing), Resend (email delivery),
          Stripe (billing), and Supabase (database/storage).
        </p>
      </div>
    </div>
  );
}
