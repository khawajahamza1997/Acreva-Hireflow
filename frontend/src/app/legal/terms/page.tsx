import Link from "next/link";

export default function TermsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <Link href="/" className="text-electric text-sm font-semibold">
        ← Back
      </Link>
      <h1 className="text-3xl font-extrabold mt-6">Terms of Service</h1>
      <p className="text-sm text-slate-500 mt-2">Last updated: June 2026</p>
      <div className="prose prose-sm mt-8 space-y-4 text-slate-700">
        <p>
          Acreva HireFlow provides AI-assisted recruitment workflow tools. By using the service you agree
          that AI-generated scores and suggestions are assistive only and that all hiring decisions remain
          your responsibility.
        </p>
        <p>
          You are responsible for lawful processing of candidate personal data, including obtaining any
          required consents under applicable employment and privacy laws.
        </p>
        <p>
          Subscriptions renew monthly unless canceled. Free trials convert to paid plans unless canceled
          before the trial ends.
        </p>
        <p>
          Questions:{" "}
          <a href="mailto:support@acreva.com" className="text-electric">
            support@acreva.com
          </a>
        </p>
      </div>
    </div>
  );
}
