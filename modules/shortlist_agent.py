# ============================================================
# shortlist_agent.py
# ============================================================
# Purpose: Auto-shortlist the top N candidates by score.
#
# This is one of the main selling points of the product.
# The recruiter picks how many to shortlist (e.g. top 3, 5, 10)
# and the system does the rest — sorts, marks, and updates Sheets.
#
# Functions:
#   get_shortlist_candidates()  → Returns top N from a DataFrame
#   run_auto_shortlist()        → Marks them in Google Sheets
#   get_shortlisted()           → Fetches already-shortlisted rows
#   remove_from_shortlist()     → Allows recruiter to undo
# ============================================================

import pandas as pd
from modules.sheets_utils import get_all_candidates, update_candidate


# ------------------------------------------------------------
# CORE SHORTLIST LOGIC
# ------------------------------------------------------------

def get_shortlist_candidates(df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Takes the full candidate DataFrame and returns the top N
    candidates sorted by score (highest first).

    Only includes candidates who have been scored (score > 0).
    Skips anyone already marked as Rejected.

    Args:
        df    : DataFrame from sheets_utils.get_all_candidates()
        top_n : How many candidates to shortlist (default 5)

    Returns a filtered, sorted DataFrame.
    """
    if df.empty or "score" not in df.columns:
        return pd.DataFrame()

    # Work on a copy — never mutate the original
    scored = df.copy()

    # Keep only rows that have a numeric score above 0
    scored["score"] = pd.to_numeric(scored["score"], errors="coerce")
    scored = scored[scored["score"] > 0]

    # Exclude rejected candidates — recruiter already decided on them
    if "status" in scored.columns:
        scored = scored[scored["status"] != "Rejected"]

    if scored.empty:
        return pd.DataFrame()

    # Sort by score descending and take top N
    shortlisted = scored.sort_values("score", ascending=False).head(top_n)

    return shortlisted.reset_index(drop=True)


def run_auto_shortlist(top_n: int = 5) -> dict:
    """
    The main function called from app.py when recruiter clicks
    "Auto Shortlist Top Candidates".

    Steps:
      1. Reads all candidates from Google Sheets
      2. Sorts by score, picks top N
      3. Updates each one: shortlisted=Yes, status=Shortlisted
      4. Returns a summary dict for the UI to display

    Returns:
    {
        "shortlisted_ids": ["A1B2C3D4", ...],
        "shortlisted_names": ["Jane Smith", ...],
        "count": 5,
        "error": None
    }
    """
    try:
        df = get_all_candidates()

        if df.empty:
            return _error_result("No candidates found in the sheet.")

        top_candidates = get_shortlist_candidates(df, top_n)

        if top_candidates.empty:
            return _error_result(
                "No scored candidates found. Please score candidates before shortlisting."
            )

        shortlisted_ids = []
        shortlisted_names = []

        for _, row in top_candidates.iterrows():
            candidate_id = row.get("candidate_id", "")
            name = row.get("name", "Unknown")

            if not candidate_id:
                continue

            # Update the candidate's record in Google Sheets
            update_candidate(candidate_id, {
                "shortlisted": "Yes",
                "status": "Shortlisted"
            })

            shortlisted_ids.append(candidate_id)
            shortlisted_names.append(name)

        return {
            "shortlisted_ids": shortlisted_ids,
            "shortlisted_names": shortlisted_names,
            "count": len(shortlisted_ids),
            "error": None
        }

    except Exception as e:
        return _error_result(str(e))


# ------------------------------------------------------------
# READ SHORTLISTED
# ------------------------------------------------------------

def get_shortlisted_candidates() -> pd.DataFrame:
    """
    Returns only the candidates currently marked as shortlisted.
    Used in the dashboard and outreach sections to show who to contact.
    """
    df = get_all_candidates()

    if df.empty or "shortlisted" not in df.columns:
        return pd.DataFrame()

    shortlisted = df[df["shortlisted"].str.strip().str.lower() == "yes"].copy()

    # Sort by score so highest-scoring appears first
    shortlisted["score"] = pd.to_numeric(shortlisted["score"], errors="coerce")
    shortlisted = shortlisted.sort_values("score", ascending=False)

    return shortlisted.reset_index(drop=True)


# ------------------------------------------------------------
# UNDO — REMOVE FROM SHORTLIST
# ------------------------------------------------------------

def remove_from_shortlist(candidate_id: str) -> bool:
    """
    Allows recruiter to undo a shortlist decision.
    Reverts status back to "Scored" and sets shortlisted to "No".

    Returns True if successful, False if not.
    """
    try:
        update_candidate(candidate_id, {
            "shortlisted": "No",
            "status": "Scored"
        })
        return True
    except Exception:
        return False


# ------------------------------------------------------------
# SUMMARY STATS (used by dashboard)
# ------------------------------------------------------------

def get_shortlist_summary(df: pd.DataFrame) -> dict:
    """
    Returns a quick summary dict for the dashboard KPI cards.

    Args:
        df : Full candidate DataFrame from get_all_candidates()

    Returns:
    {
        "total": 20,
        "scored": 15,
        "shortlisted": 5,
        "strong_fit": 6,
        "moderate_fit": 7,
        "weak_fit": 2
    }
    """
    if df.empty:
        return {
            "total": 0,
            "scored": 0,
            "shortlisted": 0,
            "strong_fit": 0,
            "moderate_fit": 0,
            "weak_fit": 0
        }

    total = len(df)

    scored = len(df[pd.to_numeric(df.get("score", pd.Series()), errors="coerce") > 0])

    shortlisted = len(
        df[df.get("shortlisted", pd.Series()).str.strip().str.lower() == "yes"]
    ) if "shortlisted" in df.columns else 0

    status_col = df.get("score_status", pd.Series(dtype=str))
    strong_fit    = len(df[status_col == "Strong Fit"])
    moderate_fit  = len(df[status_col == "Moderate Fit"])
    weak_fit      = len(df[status_col == "Weak Fit"])

    return {
        "total": total,
        "scored": scored,
        "shortlisted": shortlisted,
        "strong_fit": strong_fit,
        "moderate_fit": moderate_fit,
        "weak_fit": weak_fit
    }


# ------------------------------------------------------------
# ERROR HELPER
# ------------------------------------------------------------

def _error_result(message: str) -> dict:
    return {
        "shortlisted_ids": [],
        "shortlisted_names": [],
        "count": 0,
        "error": message
    }
