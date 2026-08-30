export const STRONG_MATCH = "Strong Match";
export const GOOD_MATCH = "Good Match";
export const POTENTIAL_MATCH = "Potential Match";
export const LOW_MATCH = "Low Match";

export const TIER_OPTIONS = [STRONG_MATCH, GOOD_MATCH, POTENTIAL_MATCH, LOW_MATCH];

export function tierBadgeClass(tier?: string): string {
  switch (tier) {
    case STRONG_MATCH:
      return "bg-green-50 text-green-700 border border-green-200";
    case GOOD_MATCH:
      return "bg-emerald-50 text-emerald-700 border border-emerald-200";
    case POTENTIAL_MATCH:
      return "bg-amber-50 text-amber-700 border border-amber-200";
    case LOW_MATCH:
      return "bg-slate-100 text-slate-600 border border-slate-200";
    default:
      return "bg-slate-50 text-slate-500 border border-slate-200";
  }
}

export function requirementResultIcon(result: string): string {
  if (result === "meets") return "✓"; // check
  if (result === "does_not_meet") return "✗"; // cross
  return "⚠"; // warning
}

export function requirementResultClass(result: string): string {
  if (result === "meets") return "text-green-600";
  if (result === "does_not_meet") return "text-red-600";
  return "text-amber-600";
}
