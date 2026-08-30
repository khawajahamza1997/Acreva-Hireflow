export type StructuredRequirements = {
  required_skills: string;
  preferred_skills: string;
  min_experience_years: string;
  education: string;
  certifications: string;
  location: string;
  work_mode: string;
  work_authorization: string;
  salary_min: string;
  salary_max: string;
  industry: string;
  management_experience: boolean;
  languages: string;
  notice_period: string;
};

export type Weights = {
  required_skills: string;
  preferred_skills: string;
  experience: string;
  education: string;
  certifications: string;
  industry_experience: string;
};

export type Thresholds = {
  strong: string;
  good: string;
  potential: string;
};

export const emptyRequirements: StructuredRequirements = {
  required_skills: "",
  preferred_skills: "",
  min_experience_years: "",
  education: "",
  certifications: "",
  location: "",
  work_mode: "",
  work_authorization: "",
  salary_min: "",
  salary_max: "",
  industry: "",
  management_experience: false,
  languages: "",
  notice_period: "",
};

export const defaultWeights: Weights = {
  required_skills: "35",
  preferred_skills: "15",
  experience: "25",
  education: "15",
  certifications: "5",
  industry_experience: "5",
};

export const defaultThresholds: Thresholds = {
  strong: "90",
  good: "75",
  potential: "60",
};

export function toArray(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function rawToFormState(data: Record<string, unknown>): StructuredRequirements {
  return {
    required_skills: ((data.required_skills as string[]) || []).join(", "),
    preferred_skills: ((data.preferred_skills as string[]) || []).join(", "),
    min_experience_years: data.min_experience_years ? String(data.min_experience_years) : "",
    education: (data.education as string) || "",
    certifications: ((data.certifications as string[]) || []).join(", "),
    location: (data.location as string) || "",
    work_mode: (data.work_mode as string) || "",
    work_authorization: (data.work_authorization as string) || "",
    salary_min: data.salary_min != null ? String(data.salary_min) : "",
    salary_max: data.salary_max != null ? String(data.salary_max) : "",
    industry: (data.industry as string) || "",
    management_experience: Boolean(data.management_experience),
    languages: ((data.languages as string[]) || []).join(", "),
    notice_period: (data.notice_period as string) || "",
  };
}

export function weightsToFormState(weights: Record<string, number> | undefined): Weights {
  return {
    required_skills: String(weights?.required_skills ?? 35),
    preferred_skills: String(weights?.preferred_skills ?? 15),
    experience: String(weights?.experience ?? 25),
    education: String(weights?.education ?? 15),
    certifications: String(weights?.certifications ?? 5),
    industry_experience: String(weights?.industry_experience ?? 5),
  };
}

export function thresholdsToFormState(thresholds: Record<string, number> | undefined): Thresholds {
  return {
    strong: String(thresholds?.strong ?? 90),
    good: String(thresholds?.good ?? 75),
    potential: String(thresholds?.potential ?? 60),
  };
}

export function formToStructuredRequirements(req: StructuredRequirements) {
  return {
    required_skills: toArray(req.required_skills),
    preferred_skills: toArray(req.preferred_skills),
    min_experience_years: Number(req.min_experience_years) || 0,
    education: req.education,
    certifications: toArray(req.certifications),
    location: req.location,
    work_mode: req.work_mode,
    work_authorization: req.work_authorization,
    salary_min: req.salary_min ? Number(req.salary_min) : null,
    salary_max: req.salary_max ? Number(req.salary_max) : null,
    industry: req.industry,
    management_experience: req.management_experience,
    languages: toArray(req.languages),
    notice_period: req.notice_period,
    custom_requirements: [],
  };
}

export function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(",")}]`;
  if (value && typeof value === "object") {
    const keys = Object.keys(value as Record<string, unknown>).sort();
    return `{${keys.map((k) => `${JSON.stringify(k)}:${stableStringify((value as Record<string, unknown>)[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
