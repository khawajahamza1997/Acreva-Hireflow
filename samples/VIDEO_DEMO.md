# HireFlow — video demo script (~5 minutes)

Use this flow to record a polished product demo. All sample files are in `samples/`.

## Before recording

1. Deploy latest code (Render + Vercel)
2. Sign in at https://acreva-hireflow.vercel.app
3. Optional: delete old test data from **Jobs**, **Candidates**, **Shortlist**
4. Have these files ready:
   - `samples/jobs/senior-react-developer.txt`
   - `samples/jobs/senior-java-developer.txt`
   - `samples/cvs/01-sarah-chen-strong-match.txt`
   - `samples/cvs/02-marcus-taylor-moderate-match.txt`
   - `samples/cvs/03-jordan-lee-weak-match.txt`

---

## Scene 1 — Onboarding (90 sec)

1. **Onboarding** → Job title: `Senior React Developer`
2. Paste job from `senior-react-developer.txt` → **Continue**
   - ✅ Green banner: "Job created"
3. Upload `01-sarah-chen-strong-match.txt` → **Upload & continue**
   - ✅ Green banner: "CV uploaded and parsed"
4. **Score candidates** → ✅ "Scored 1 candidate(s)"
5. **Shortlist top 3** → ✅ shortlist message
6. **Go to dashboard** → stats show Total/Scored/Shortlisted

**Say:** "In under a minute we created a role, parsed a CV with AI, scored it, and shortlist-ready."

---

## Scene 2 — Bulk candidates (60 sec)

1. **Candidates** → upload `02-marcus-taylor-moderate-match.txt` and `03-jordan-lee-weak-match.txt`
   - ✅ success banner after each upload
2. **Scoring** → select **Senior React Developer** → **Score all**
   - ✅ Sarah highest, Jordan lowest
3. **Shortlist** → Auto-shortlist top 3
   - ✅ names listed with scores

**Say:** "AI ranks candidates automatically — strong React fit vs weak fit."

---

## Scene 3 — Second job / re-score (60 sec)

1. **Jobs** → create **Senior Java Developer** (paste from `senior-java-developer.txt`)
   - ✅ "Job created successfully"
2. **Scoring** → select **Senior Java Developer** → **Score all**
   - ✅ all 3 re-scored (Sarah lower for Java, Marcus may score differently)
3. **Shortlist** → Auto-shortlist again

**Say:** "Same candidates, different role — scores update instantly for the new job."

---

## Scene 4 — Pipeline & outreach (60 sec)

1. **Pipeline** → show kanban columns
2. **Outreach** → Demo mode **ON** → select Sarah → **Fill template** → **Send**
   - ✅ "Demo mode — email not sent"
3. **Audit Log** → show cv_uploaded, candidate_scored, email_preview

**Say:** "Full audit trail for compliance. Demo mode for safe client presentations."

---

## Scene 5 — Delete / cleanup (30 sec)

1. **Shortlist** → **Remove** one candidate
2. **Jobs** → **Delete** a test job (candidates kept)
3. **Candidates** → **Delete** a test row

**Say:** "Full CRUD — manage jobs, candidates, and shortlists."

---

## Closing line

"Acreva HireFlow: upload CVs, AI scoring, auto-shortlist, outreach, and audit — built for small recruitment agencies at $39/month."
