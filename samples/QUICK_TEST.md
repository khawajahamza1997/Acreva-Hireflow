# HireFlow — copy-paste test pack (no typing)

Use these files to test signup → onboarding → scoring → shortlist → outreach in under 5 minutes.

## Files in this folder

| File | Use for |
|------|---------|
| `jobs/senior-react-developer.txt` | Job description (copy all into Onboarding step 1) |
| `jobs/senior-java-developer.txt` | Second job for re-scoring demo |
| `cvs/01-sarah-chen-strong-match.txt` | Upload first — expect **Strong Fit** (8–10) |
| `cvs/02-marcus-taylor-moderate-match.txt` | Upload second — expect **Moderate Fit** (5–7) |
| `cvs/03-jordan-lee-weak-match.txt` | Upload third — expect **Weak Fit** (below 5) |

## Onboarding — step 1 (Create job)

**Job title** (copy this line):

```
Senior React Developer
```

**Job description:** open `jobs/senior-react-developer.txt`, select all (Ctrl+A), copy, paste into the form.

Click **Continue**.

## Onboarding — step 2 (Upload CV)

Upload all three files from `cvs/` one at a time, **or** upload only `01-sarah-chen-strong-match.txt` for a quick test.

After each upload, continue to the next step when ready.

**Tip:** On **Candidates** page you can upload the other two CVs later without redoing onboarding.

## Onboarding — steps 3–4

1. Click **Score candidates** (needs `OPENAI_API_KEY` on Render).
2. Click **Shortlist top 3**.
3. Click **Go to dashboard**.

## What you should see

| Page | Expected |
|------|----------|
| Dashboard | Total: 3 (or 1), Scored/Shortlisted counts update |
| Candidates | Sarah Chen, Marcus Taylor, Jordan Lee |
| Scoring | Sarah highest score, Jordan lowest |
| Pipeline | Cards in New Applicant → Scored → Shortlisted columns |
| Shortlist | Sarah (and possibly Marcus) shortlisted |
| Outreach | Pick Sarah → Demo mode ON → Send (safe preview) |
| Audit Log | cv_uploaded, candidate_scored, candidate_shortlisted entries |

## Outreach test (safe)

1. Go to **Outreach**
2. Keep **Demo mode** checked
3. Select **Sarah Chen**
4. Template: **Interview invitation**
5. Click **Fill template for candidate** → **Send**
6. Message: "Demo mode — email not sent."

## If scoring fails

Render env var `OPENAI_API_KEY` must be set and valid. Redeploy after adding it.
