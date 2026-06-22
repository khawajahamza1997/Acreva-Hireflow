# ============================================================
# demo_utils.py
# ============================================================
# Helpers for client demos: load sample CVs/JD and run the
# full workflow in a few clicks during sales presentations.
# ============================================================

import os
from modules.cv_parser import parse_local_cv_file
from modules.sheets_utils import append_candidate, candidate_exists, get_all_candidates, update_candidate
from modules.scoring_agent import score_candidate
from modules.shortlist_agent import run_auto_shortlist

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_CV_DIR = os.path.join(PROJECT_ROOT, "data", "sample_candidates")
SAMPLE_JD_PATH = os.path.join(PROJECT_ROOT, "data", "sample_job_description.txt")
DEFAULT_JOB_TITLE = "Sales Executive – B2B SaaS"


def load_sample_job_description() -> str:
    """Returns the bundled sample job description text."""
    if not os.path.exists(SAMPLE_JD_PATH):
        return ""
    with open(SAMPLE_JD_PATH, encoding="utf-8") as f:
        return f.read()


def get_sample_cv_files() -> list[str]:
    """Returns paths to sample CV files on disk."""
    if not os.path.exists(SAMPLE_CV_DIR):
        return []
    return sorted(
        os.path.join(SAMPLE_CV_DIR, name)
        for name in os.listdir(SAMPLE_CV_DIR)
        if name.lower().endswith((".txt", ".pdf", ".docx"))
    )


def import_sample_candidates(job_title: str = DEFAULT_JOB_TITLE) -> dict:
    """
    Parses sample CV files and saves new candidates to Google Sheets.

    Returns:
        {
            "imported": 3,
            "skipped": 2,
            "names": ["Sarah Johnson", ...],
            "errors": []
        }
    """
    result = {"imported": 0, "skipped": 0, "names": [], "errors": []}

    for filepath in get_sample_cv_files():
        try:
            candidate = parse_local_cv_file(filepath)
            email = candidate.get("email", "")

            if candidate.get("parse_error"):
                result["errors"].append(f"{os.path.basename(filepath)}: {candidate['parse_error']}")
                continue

            if candidate_exists(email):
                result["skipped"] += 1
                continue

            candidate_id = append_candidate(candidate, job_title)
            candidate["candidate_id"] = candidate_id
            result["imported"] += 1
            result["names"].append(candidate.get("name", "Unknown"))

        except Exception as e:
            result["errors"].append(f"{os.path.basename(filepath)}: {e}")

    return result


def score_all_unscored(job_description: str) -> dict:
    """Scores every candidate in the sheet that has no score yet."""
    import pandas as pd

    result = {"scored": 0, "names": [], "errors": []}
    df = get_all_candidates()

    if df.empty:
        return result

    unscored_mask = pd.to_numeric(df.get("score", pd.Series()), errors="coerce").isna() | \
                    (pd.to_numeric(df.get("score", pd.Series()), errors="coerce") == 0)
    unscored_df = df[unscored_mask]

    for _, row in unscored_df.iterrows():
        try:
            candidate_dict = row_to_scoring_dict(row)
            scoring = score_candidate(candidate_dict, job_description)

            if scoring.get("error"):
                result["errors"].append(f"{row.get('name')}: {scoring['error']}")
                continue

            update_candidate(row["candidate_id"], {
                "score":        scoring["score"],
                "score_status": scoring["status"],
                "score_reason": " | ".join(scoring.get("reason", [])),
                "status":       "Scored"
            })
            result["scored"] += 1
            result["names"].append(row.get("name", "Unknown"))

        except Exception as e:
            result["errors"].append(f"{row.get('name', 'Candidate')}: {e}")

    return result


def run_full_client_demo(job_description: str, top_n: int = 3) -> dict:
    """
    One-click demo: import samples → score all → shortlist top N.

    Returns a summary dict for the UI.
    """
    summary = {
        "imported": 0,
        "skipped": 0,
        "scored": 0,
        "shortlisted": 0,
        "shortlisted_names": [],
        "errors": []
    }

    imported = import_sample_candidates()
    summary["imported"] = imported["imported"]
    summary["skipped"] = imported["skipped"]
    summary["errors"].extend(imported["errors"])

    scored = score_all_unscored(job_description)
    summary["scored"] = scored["scored"]
    summary["errors"].extend(scored["errors"])

    shortlist = run_auto_shortlist(top_n)
    if shortlist.get("error"):
        summary["errors"].append(shortlist["error"])
    else:
        summary["shortlisted"] = shortlist["count"]
        summary["shortlisted_names"] = shortlist["shortlisted_names"]

    return summary


def row_to_scoring_dict(row) -> dict:
    """Builds the candidate dict expected by scoring_agent from a sheet row."""
    return {
        "name":             row.get("name", ""),
        "current_role":     row.get("current_role", ""),
        "skills":           row.get("skills", ""),
        "experience_years": row.get("experience_years", 0),
        "education":        row.get("education", ""),
        "summary":          row.get("notes", ""),
        "raw_text":         row.get("cv_text", "") or "",
    }
