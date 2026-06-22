# Acreva HireFlow v2 — Product Setup

Full-stack SaaS: **Next.js frontend** + **FastAPI backend** + **Supabase** (database, auth, file storage).

The original Streamlit app (`app.py`) remains for local demos. The new product lives in `frontend/` and `backend/`.

---

## 1. Create Supabase project (free)

1. Go to [supabase.com](https://supabase.com) → New project  
2. Open **SQL Editor** → **New query**  
3. **Do not paste the file path.** Open this file on your computer:
   `c:\Users\Ali\Acreva_HireFlow\supabase\migrations\001_initial.sql`
4. Select **all** the SQL inside (Ctrl+A), **copy** it, paste into the Supabase editor, click **Run**
5. You should see **Success. No rows returned** (that is normal)
6. Copy from **Project Settings → API**:
   - Project URL → `SUPABASE_URL`
   - `anon` key → frontend (optional later)
   - `service_role` key → `SUPABASE_SERVICE_ROLE_KEY`
   - JWT Secret → `SUPABASE_JWT_SECRET`
7. **Authentication → Providers → Email** — enable email signup

---

## 2. Backend setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Or put keys in the project root `.env` (also supported)
# Fill in .env with Supabase, OpenAI, Resend, Stripe keys
uvicorn app.main:app --reload --port 8000
```

**Windows + Anaconda:** if you use Anaconda Python, install deps with:
`C:\Users\Ali\anaconda3\python.exe -m pip install -r requirements.txt`

API docs: http://localhost:8000/docs

---

## 3. Frontend setup

```powershell
cd frontend
npm install
copy .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

App: http://localhost:3000

---

## 4. Third-party services

| Service | Purpose | Free tier |
|---------|---------|-----------|
| **Supabase** | DB, auth, CV file storage | Yes |
| **OpenAI** | CV parse + scoring | Pay per use |
| **Resend** | Transactional email | 100 emails/day free |
| **Stripe** | Billing + 14-day trial | Test mode free |

### Stripe setup
1. Create product + $39/mo price in Stripe Dashboard  
2. Copy `price_...` → `STRIPE_PRICE_ID`  
3. Add webhook endpoint: `https://your-api.onrender.com/api/v1/billing/webhook`  
4. Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`

### Resend setup
1. Verify your domain (or use Resend test domain for dev)  
2. Copy API key → `RESEND_API_KEY`

---

## 5. Deploy online (free tier)

### Frontend → Vercel (free)
1. Push repo to GitHub  
2. Import project in Vercel, set root to `frontend/`  
3. Env: `NEXT_PUBLIC_API_URL=https://your-api.onrender.com`  
4. Deploy

### Backend → Render (free)
1. New Web Service → connect repo  
2. Use `render.yaml` or set root `backend/`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`  
3. Add all env vars from `backend/.env.example`  
4. Set `FRONTEND_URL` to your Vercel URL  
5. Set `CORS_ORIGINS` to your Vercel URL

**Note:** Render free tier sleeps after inactivity (slow cold starts).

---

## Features included

- Login / signup with organization per account  
- Multi-tenant data isolation (Supabase RLS)  
- CV file upload + storage + AI parsing  
- AI scoring, auto-shortlist, pipeline board  
- Candidate detail page with score + audit history  
- Resend email outreach + editable templates  
- Team invites (owner / recruiter / viewer)  
- Audit log  
- Stripe billing + 14-day trial  
- Landing page, Terms, Privacy Policy  
- Onboarding wizard  
- Demo mode for safe email previews  

---

## Mobile app (later)

The FastAPI backend is ready for React Native — use the same `/api/v1` endpoints and JWT auth.

---

Support: support@acreva.com
