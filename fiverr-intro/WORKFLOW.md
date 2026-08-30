# Fiverr Intro Video — Software & Workflow

Complete guide for **Khawaja Hamza / Acreva**. Target: **45–55 second** hybrid intro video.

## What you are making

| Time | Content |
|------|---------|
| 0:00–0:12 | You on camera — hook (Block A) |
| 0:12–0:35 | HireFlow screen demo + voiceover (Block B) |
| 0:35–0:50 | You on camera — call to action (Block C) |

**Fiverr rules:** 20–60 sec, you must appear on camera, English, min 1280×720, 16:9 MP4, no contact info in video.

---

## Step 1 — Script

**Software:** Notepad, Google Docs, or Word

Copy from [`SCRIPT.txt`](SCRIPT.txt) or open it while recording.

---

## Step 2 — Prepare HireFlow demo

Pick **one** app to show on screen:

### Option A — Next.js (polished SaaS UI)

```powershell
cd frontend
npm run dev
```

Open http://localhost:3000. Follow [`samples/QUICK_TEST.md`](../samples/QUICK_TEST.md) to load job + CVs + score + shortlist.

### Option B — Streamlit (fast local demo)

```powershell
streamlit run app.py
```

Keep **Client demo mode ON** in sidebar. Use **Client Demo** tab → **Run full client demo**.

**Browser:** Chrome or Edge, 100% zoom, bookmarks bar hidden.

**3 scenes to record (~7 sec each):**

1. CV upload / candidate list
2. Scoring with job description and AI scores
3. Shortlist + outreach email preview (demo mode = no send)

---

## Step 3 — Record screen clips

**Recommended:** OBS Studio (free) — https://obsproject.com

| Software | When to use |
|----------|-------------|
| **OBS Studio** | Best quality, 1920×1080 canvas |
| **Xbox Game Bar** (`Win + G`) | Quick clips, no install |
| **ShareX** | Lightweight alternative |

See [`RECORDING_CHECKLIST.md`](RECORDING_CHECKLIST.md) for OBS settings and clip names.

---

## Step 4 — Record face clips

| Software | When to use |
|----------|-------------|
| **Phone + tripod** | Best image quality |
| **OBS Studio** (webcam source) | Same app as screen recording |
| **Windows Camera** | Simple webcam clips |

Open `SCRIPT.txt` Block A and Block C on a second monitor or phone below the camera.

---

## Step 5 — Edit in CapCut

**Download:** CapCut desktop (free)

See [`CAPCUT_GUIDE.md`](CAPCUT_GUIDE.md) for timeline layout and export settings.

Import [`subtitles.srt`](subtitles.srt) or use auto-captions.

---

## Step 6 — Re-encode (only if Fiverr rejects upload)

**HandBrake** — preset: Web → Gmail Large 720p30 → save as `acreva-intro.mp4`

---

## Step 7 — Upload

See [`UPLOAD_CHECKLIST.md`](UPLOAD_CHECKLIST.md)

URL: https://fiverr.com/sellers/acreva/edit?focused_section=intro_video

---

## Recommended free stack

```
Google Docs / SCRIPT.txt  →  script
HireFlow in Chrome        →  demo on screen
OBS Studio                →  record screen + face
CapCut desktop            →  edit + subtitles
Fiverr profile            →  upload
```

**Estimated time:** 2–3 hours total.
