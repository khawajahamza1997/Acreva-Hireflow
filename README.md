# Acreva HireFlow

**AI-Assisted Recruitment Workflow — From CV to Shortlist to Interview**

> AI-assisted scoring only. Final hiring decision remains with the recruiter.

---

## What This App Does

Acreva HireFlow helps small businesses and recruitment agencies remove the manual
work from candidate screening. It does NOT make hiring decisions — it assists
recruiters by doing the time-consuming groundwork.

**Core workflow:**
1. Upload candidate CVs (PDF or text)
2. Paste a job description
3. AI parses and scores each candidate
4. Auto-shortlist top candidates
5. Send outreach emails to shortlisted candidates
6. Track interview stages in a live dashboard

---

## Folder Structure

```
Acreva_HireFlow/
├── app.py                        # Main Streamlit app (entry point)
├── requirements.txt              # All Python libraries needed
├── .env                          # Your API keys and credentials (never share)
├── credentials.json              # Google Cloud service account key (never share)
├── README.md                     # This file
│
├── modules/
│   ├── __init__.py               # Makes modules a Python package
│   ├── cv_parser.py              # Reads and extracts info from CVs
│   ├── scoring_agent.py          # Scores candidates using OpenAI
│   ├── shortlist_agent.py        # Auto-shortlists top candidates
│   ├── outreach_agent.py         # Sends emails to candidates
│   ├── sheets_utils.py           # Reads/writes data in Google Sheets
│   └── dashboard_utils.py        # Prepares data and charts for dashboard
│
├── assets/
│   └── style.css                 # Premium UI styling (injected into Streamlit)
│
└── data/
    ├── sample_job_description.txt  # Example job description for testing
    └── sample_candidates/          # Put sample PDF CVs here for testing
```

---

## Setup Instructions

### Step 1 — Install Python libraries
```bash
pip install -r requirements.txt
```

### Step 2 — Set up Google Sheets
1. Go to https://console.cloud.google.com
2. Create a new project
3. Enable Google Sheets API and Google Drive API
4. Create a Service Account
5. Download the JSON key and rename it `credentials.json`
6. Place `credentials.json` in the `Acreva_HireFlow/` root folder
7. Create a new Google Sheet named `Acreva_HireFlow_CRM`
8. Share that sheet with the service account email (with Editor access)

### Step 3 — Configure .env
Fill in your real values in the `.env` file.

### Step 4 — Run the app
```bash
streamlit run app.py
```

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python | Core language |
| Streamlit | Web app framework |
| OpenAI GPT-4 | CV scoring and analysis |
| Google Sheets API | CRM / candidate database |
| pdfplumber | PDF text extraction |
| python-docx | Word document parsing |
| smtplib (Gmail) | Outreach email sending |
| pandas | Data handling and display |
| plotly | Dashboard charts |

---

## Important Notes

- This app is a **recruitment assistant**, not a replacement for recruiter judgment
- All scores are AI-suggested — always review before making final decisions
- Google Sheets is used as the database for MVP simplicity
- Email sending uses Gmail SMTP — use an App Password, not your real password

---

*Built by Acreva — Practical AI for growing businesses.*
