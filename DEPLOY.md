# Deploy Acreva HireFlow Online — Full Step-by-Step Guide

Deploy the **Next.js frontend** to **Vercel** (free) and the **FastAPI backend** to **Render** (free).  
**Supabase** is already your database (you completed the SQL migration).

**Order:** GitHub → Backend (Render) → Frontend (Vercel) → Connect URLs → Test

---

## Before you start — checklist

- [ ] Supabase project created + `001_initial.sql` run successfully  
- [ ] App works locally (`localhost:3000` + `localhost:8000`)  
- [ ] You have these keys ready (from your local `.env`):
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`
  - `OPENAI_API_KEY`
- [ ] A **GitHub account** (free): https://github.com  
- [ ] **Never commit** `.env` or `credentials.json` (already in `.gitignore`)

---

## Part 1 — Put code on GitHub

> Your PC may have git at `C:\Users\Ali` (home folder). Create a **separate repo** for HireFlow only.

### 1.1 Create a new GitHub repository

1. Go to https://github.com/new  
2. Repository name: `Acreva-HireFlow` (or any name)  
3. Set to **Private** (recommended — keeps code off public search)  
4. **Do not** add README, .gitignore, or license (you already have files)  
5. Click **Create repository**

### 1.2 Initialize git inside the project folder only

Open PowerShell:

```powershell
cd c:\Users\Ali\Acreva_HireFlow
git init
git add .
git status
```

**Verify** `.env` and `credentials.json` are **NOT** listed. If they appear, stop and check `.gitignore`.

```powershell
git commit -m "Acreva HireFlow v2 — web app, API, Supabase schema"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Acreva-HireFlow.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. Sign in if prompted.

---

## Part 2 — Deploy the backend (Render)

Deploy the API **first** — you need its URL for the frontend.

### 2.1 Create a Render account

1. Go to https://render.com  
2. Sign up (free) — **Sign in with GitHub** is easiest  

### 2.2 Create a Web Service

**Recommended: use Docker (avoids Python 3.14 build errors on Render)**

1. Click **New +** → **Web Service**  
2. Connect your GitHub account if asked  
3. Select the **Acreva-HireFlow** repository  
4. Configure:

| Setting | Value |
|---------|--------|
| **Name** | `hireflow-api` |
| **Region** | Choose closest to you |
| **Branch** | `main` |
| **Root Directory** | `backend` |
| **Language / Runtime** | **Docker** *(not Python)* |
| **Dockerfile Path** | `Dockerfile` |
| **Instance Type** | **Free** |

Render will build using `backend/Dockerfile` which pins **Python 3.11** — no Rust/pydantic compile errors.

<details>
<summary>Alternative: Native Python runtime (only if you won't use Docker)</summary>

| Setting | Value |
|---------|--------|
| **Language** | Python 3 |
| **Build Command** | `pip install --upgrade pip && pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

You **must** add environment variable **`PYTHON_VERSION`** = **`3.11.11`** before deploy.
Without it, Render defaults to Python 3.14 and the build fails on `pydantic-core`.

</details>

### 2.3 Add environment variables (Render → Environment)

Click **Advanced** → **Add Environment Variable**. Add **every** row below:

| Key | Value |
|-----|--------|
| `SUPABASE_URL` | From Supabase → Settings → API → Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | From Supabase → Settings → API → `service_role` |
| `SUPABASE_JWT_SECRET` | From Supabase → Settings → API → JWT Secret |
| `OPENAI_API_KEY` | Your OpenAI key |
| `FRONTEND_URL` | `https://PLACEHOLDER.vercel.app` *(update after Part 3)* |
| `CORS_ORIGINS` | `https://PLACEHOLDER.vercel.app` *(update after Part 3)* |
| `SUPPORT_EMAIL` | `support@acreva.com` (or your email) |

**Optional for now** (add later):

| Key | When needed |
|-----|-------------|
| `RESEND_API_KEY` | When sending real emails |
| `EMAIL_FROM` | `Acreva HireFlow <onboarding@resend.dev>` for testing |
| `STRIPE_SECRET_KEY` | When enabling billing |
| `STRIPE_PRICE_ID` | When enabling billing |
| `STRIPE_WEBHOOK_SECRET` | After Stripe webhook setup |

### 2.4 Deploy

1. Click **Create Web Service**  
2. Wait 3–8 minutes for the first build  
3. When status is **Live**, copy your URL, e.g.  
   `https://hireflow-api.onrender.com`

### 2.5 Test the API

Open in browser:

```
https://YOUR-API-URL.onrender.com/health
```

You should see:

```json
{"status":"ok","product":"Acreva HireFlow"}
```

**First request after idle:** Render free tier sleeps — first load may take **30–60 seconds**. That is normal.

---

## Part 3 — Deploy the frontend (Vercel)

### 3.1 Create a Vercel account

1. Go to https://vercel.com  
2. Sign up → **Continue with GitHub**

### 3.2 Import the project

1. Click **Add New…** → **Project**  
2. Import **Acreva-HireFlow** from GitHub  
3. Configure:

| Setting | Value |
|---------|--------|
| **Framework Preset** | Next.js (auto-detected) |
| **Root Directory** | Click **Edit** → set to `frontend` |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | `.next` (default) |

### 3.3 Environment variable

Under **Environment Variables**, add:

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-API-URL.onrender.com` |

Use your **Render URL from Part 2** — no trailing slash.

Example:

```
NEXT_PUBLIC_API_URL=https://hireflow-api.onrender.com
```

### 3.4 Deploy

1. Click **Deploy**  
2. Wait 2–5 minutes  
3. Copy your live URL, e.g. `https://acreva-hireflow.vercel.app`

---

## Part 4 — Connect frontend and backend

Go back to **Render** → your `hireflow-api` service → **Environment**.

Update these two variables with your **real Vercel URL**:

| Key | Value |
|-----|--------|
| `FRONTEND_URL` | `https://your-app.vercel.app` |
| `CORS_ORIGINS` | `https://your-app.vercel.app` |

Click **Save Changes**. Render will redeploy automatically (~2 min).

---

## Part 5 — Supabase settings (production)

In Supabase Dashboard → **Authentication**:

1. **Providers → Email** — enabled  
2. **URL Configuration** (optional but recommended):
   - **Site URL:** `https://your-app.vercel.app`
   - **Redirect URLs:** add `https://your-app.vercel.app/**`

---

## Part 6 — Test your live app

Open `https://your-app.vercel.app` and run through:

1. **Landing page** loads  
2. **Start free trial** → create account  
3. **Onboarding** → create job → upload CV  
4. **Scoring** → shortlist  
5. **Outreach** → preview email (demo mode)  
6. **Dashboard** shows data  

If signup fails, check Render logs: **Render → hireflow-api → Logs**

---

## Part 7 — Optional: Stripe billing (when ready to charge)

1. https://dashboard.stripe.com → **Products** → create **Starter $39/mo**  
2. Copy **Price ID** (`price_...`)  
3. Add to Render env: `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_TRIAL_DAYS=14`  
4. **Developers → Webhooks → Add endpoint**  
   - URL: `https://YOUR-API-URL.onrender.com/api/v1/billing/webhook`  
   - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`  
5. Copy **Signing secret** → Render env: `STRIPE_WEBHOOK_SECRET`

---

## Part 8 — Optional: Resend email (when ready to send)

1. https://resend.com → sign up  
2. **API Keys** → create key → add to Render: `RESEND_API_KEY`  
3. For testing use: `EMAIL_FROM=Acreva HireFlow <onboarding@resend.dev>`  
4. For production, verify your own domain in Resend  

---

## Part 9 — Optional: Custom domain

### Vercel (frontend)
1. Vercel project → **Settings → Domains**  
2. Add e.g. `app.acreva.com`  
3. Add the DNS records Vercel shows at your domain registrar  

### Render (backend)
1. Render service → **Settings → Custom Domains**  
2. Add e.g. `api.acreva.com`  
3. Update Vercel env: `NEXT_PUBLIC_API_URL=https://api.acreva.com`  
4. Update Render env: `CORS_ORIGINS` and `FRONTEND_URL` to your app domain  

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| **Signup/login fails** | Check Render logs; verify `SUPABASE_*` keys on Render |
| **CORS error in browser** | `CORS_ORIGINS` on Render must **exactly** match Vercel URL (https, no trailing slash) |
| **API very slow first time** | Render free tier cold start — wait 60s or upgrade to $7/mo |
| **CV upload fails** | Check OpenAI key on Render; check Supabase Storage bucket `cvs` exists |
| **"Stripe not configured"** | Normal until you add Stripe keys — billing page optional for demos |
| **Build fails on Render** | Set **Root Directory** to `backend` and env `PYTHON_VERSION=3.11.11` (not 3.14) |
| **pydantic-core / maturin / Rust error** | Python version too new — force **3.11.11** (see above) |
| **Build fails on Vercel** | Ensure **Root Directory** is `frontend` |

---

## Your live URLs (fill in after deploy)

| Service | URL |
|---------|-----|
| Frontend | `https://________________.vercel.app` |
| Backend | `https://________________.onrender.com` |
| Supabase | `https://________________.supabase.co` |

---

## Cost summary (starting out)

| Service | Cost |
|---------|------|
| Vercel | $0 |
| Render (free) | $0 (sleeps when idle) |
| Supabase | $0 (free tier) |
| OpenAI | Pay per CV (~$0.05–0.15 per parse+score) |

**Total fixed cost to start: $0/month** (+ OpenAI usage)

---

*After deploy, share your Vercel link with pilot clients — no laptop required.*
