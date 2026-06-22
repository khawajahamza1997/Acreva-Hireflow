# ============================================================
# sheets_utils.py
# ============================================================
# Purpose: All Google Sheets read/write operations.
# This acts as the CRM/database layer for the app.
#
# Functions:
#   get_sheet()            → Connect and return the worksheet
#   init_sheet()           → Create headers if sheet is empty
#   append_candidate()     → Add a new candidate row
#   get_all_candidates()   → Read all rows as a DataFrame
#   update_candidate()     → Update specific fields for a candidate
#   candidate_exists()     → Check if a candidate is already stored
# ============================================================
#
# GOOGLE SHEETS SETUP — READ THIS BEFORE RUNNING
# ------------------------------------------------
# Step 1: Go to https://console.cloud.google.com
# Step 2: Create a new project (e.g. "acreva-hireflow")
# Step 3: In the sidebar go to "APIs & Services" → "Library"
#         Search and ENABLE both:
#           - Google Sheets API
#           - Google Drive API
# Step 4: Go to "APIs & Services" → "Credentials"
#         Click "Create Credentials" → "Service Account"
#         Give it any name, click Done
# Step 5: Click the service account you just created
#         Go to "Keys" tab → "Add Key" → "Create new key" → JSON
#         A file downloads — rename it to: credentials.json
#         Place it in: C:/Users/Ali/Acreva_HireFlow/credentials.json
# Step 6: Open credentials.json and copy the "client_email" value
#         It looks like: something@your-project.iam.gserviceaccount.com
# Step 7: Go to Google Sheets (sheets.google.com)
#         Create a new spreadsheet named exactly: Acreva_HireFlow_CRM
#         Click Share → paste the client_email → give Editor access
# Step 8: You're done. The app will now read and write to that sheet.
# ============================================================

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

# Google APIs we need access to
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# These are all the columns in our CRM sheet — in order
SHEET_COLUMNS = [
    "candidate_id",
    "created_at",
    "name",
    "email",
    "phone",
    "current_role",
    "skills",
    "experience_years",
    "education",
    "filename",
    "job_title",
    "score",
    "score_status",
    "score_reason",
    "shortlisted",
    "contacted",
    "interview_date",
    "interview_time",
    "interview_stage",
    "status",
    "cv_text",
    "notes"
]


# ------------------------------------------------------------
# CONNECTION
# ------------------------------------------------------------

def get_sheet():
    """
    Authenticates with Google and returns the main worksheet object.
    Called at the start of every sheets operation.
    """
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    sheet_name = os.getenv("GOOGLE_SHEET_NAME", "Acreva_HireFlow_CRM")

    if not os.path.exists(creds_path):
        raise FileNotFoundError(
            f"credentials.json not found at: {creds_path}\n"
            "Please follow the Google Sheets setup instructions in sheets_utils.py"
        )

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open(sheet_name)

    # Use the first worksheet (tab) in the spreadsheet
    return spreadsheet.sheet1


def init_sheet():
    """
    Checks if the sheet has headers. If it's empty, writes the header row.
    Adds any missing columns to existing sheets without deleting data.
    Safe to call every time the app starts — it won't overwrite existing data.
    """
    sheet = get_sheet()
    existing = sheet.row_values(1)

    if not existing:
        sheet.append_row(SHEET_COLUMNS)
        return "Sheet initialised with headers."

    missing = [col for col in SHEET_COLUMNS if col not in existing]
    if missing:
        sheet.update("1:1", [existing + missing])
        return f"Sheet updated — added columns: {', '.join(missing)}."

    return "Sheet already initialised."


# ------------------------------------------------------------
# WRITE
# ------------------------------------------------------------

def append_candidate(candidate: dict, job_title: str = "") -> str:
    """
    Adds a new candidate row to Google Sheets.
    'candidate' is the dict returned by cv_parser.process_uploaded_cv()
    Returns the candidate_id assigned to this record.
    """
    sheet = get_sheet()

    candidate_id = str(uuid.uuid4())[:8].upper()  # Short unique ID e.g. "A1B2C3D4"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    row_data = {
        "candidate_id":     candidate_id,
        "created_at":       created_at,
        "name":             candidate.get("name", ""),
        "email":            candidate.get("email", ""),
        "phone":            candidate.get("phone", ""),
        "current_role":     candidate.get("current_role", ""),
        "skills":           candidate.get("skills", ""),
        "experience_years": candidate.get("experience_years", 0),
        "education":        candidate.get("education", ""),
        "filename":         candidate.get("filename", ""),
        "job_title":        job_title,
        "score":            "",
        "score_status":     "",
        "score_reason":     "",
        "shortlisted":      "No",
        "contacted":        "No",
        "interview_date":   "",
        "interview_time":   "",
        "interview_stage":  "",
        "status":           "New Applicant",
        "cv_text":          candidate.get("raw_text", "")[:5000],
        "notes":            "",
    }

    headers = sheet.row_values(1) or SHEET_COLUMNS
    row = [row_data.get(col, "") for col in headers]

    sheet.append_row(row)
    return candidate_id


def update_candidate(candidate_id: str, updates: dict):
    """
    Updates specific columns for a candidate identified by their candidate_id.

    Example usage:
        update_candidate("A1B2C3D4", {"score": 8.4, "score_status": "Strong Fit"})

    'updates' is a dict where keys are column names from SHEET_COLUMNS.
    """
    sheet = get_sheet()
    all_data = sheet.get_all_values()

    if not all_data:
        return

    headers = all_data[0]          # First row = column names
    rows = all_data[1:]            # Rest = data rows

    for i, row in enumerate(rows):
        if row and row[0] == candidate_id:
            # Found the matching row — row index in sheet is i+2 (1-indexed + header)
            sheet_row_index = i + 2

            for col_name, new_value in updates.items():
                if col_name in headers:
                    col_index = headers.index(col_name) + 1  # gspread is 1-indexed
                    sheet.update_cell(sheet_row_index, col_index, new_value)
            return


# ------------------------------------------------------------
# READ
# ------------------------------------------------------------

def get_all_candidates() -> pd.DataFrame:
    """
    Reads all candidate rows from Google Sheets and returns a pandas DataFrame.
    Returns an empty DataFrame if the sheet has no data yet.
    """
    sheet = get_sheet()
    all_data = sheet.get_all_values()

    if not all_data or len(all_data) < 2:
        # No data rows yet — return empty DataFrame with correct columns
        return pd.DataFrame(columns=SHEET_COLUMNS)

    headers = all_data[0]
    rows = all_data[1:]

    df = pd.DataFrame(rows, columns=headers)

    # Convert score column to numeric where possible
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["experience_years"] = pd.to_numeric(df["experience_years"], errors="coerce")

    return df


def candidate_exists(email: str) -> bool:
    """
    Checks if a candidate with this email is already in the sheet.
    Prevents duplicate records when uploading the same CV twice.
    Returns True if found, False if not.
    """
    if not email:
        return False

    sheet = get_sheet()
    all_data = sheet.get_all_values()

    if not all_data or len(all_data) < 2:
        return False

    headers = all_data[0]
    if "email" not in headers:
        return False

    email_col = headers.index("email")
    existing_emails = [row[email_col].lower() for row in all_data[1:] if len(row) > email_col]

    return email.lower() in existing_emails
