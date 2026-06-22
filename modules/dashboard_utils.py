# ============================================================
# dashboard_utils.py
# ============================================================
# Purpose: Prepare all data, KPI counts, and Plotly charts
# for the premium dashboard in app.py.
#
# This module never touches Google Sheets directly.
# It receives a DataFrame and returns processed data + figures.
#
# Functions:
#   get_kpi_counts()          → Dict of all KPI card numbers
#   get_pipeline_chart()      → Horizontal bar: candidates per stage
#   get_score_distribution()  → Histogram of score spread
#   get_fit_breakdown_chart() → Donut: Strong / Moderate / Weak
#   get_recent_candidates()   → Last 10 candidates for activity feed
#   get_display_columns()     → Clean column subset for tables
# ============================================================

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Brand colours — Tarhan theme (light cards, navy sidebar)
COLOR_NAVY       = "#0B1E3D"
COLOR_ELECTRIC   = "#1A6BFF"
COLOR_ORANGE     = "#FF6B2B"
COLOR_GREY_BLUE  = "#3D5A80"
COLOR_LIGHT_BLUE = "#A8C4F0"
COLOR_TEXT_DARK  = "#0B1E3D"
COLOR_TEXT_MID   = "#3D5A80"
COLOR_MUTED      = "#7A95BE"
COLOR_WHITE      = "#FFFFFF"
COLOR_SUCCESS    = "#16A34A"
COLOR_WARNING    = "#D97706"
COLOR_DANGER     = "#DC2626"
COLOR_PAGE_BG    = "#EEF2F8"

# Pipeline stage order — controls display order in charts
STAGE_ORDER = [
    "New Applicant",
    "Scored",
    "Shortlisted",
    "Contacted",
    "Interview Scheduled",
    "Rejected"
]


# ------------------------------------------------------------
# KPI COUNTS
# ------------------------------------------------------------

def get_kpi_counts(df: pd.DataFrame) -> dict:
    """
    Returns a dict of counts for all KPI cards on the dashboard.

    Args:
        df : Full candidate DataFrame from sheets_utils.get_all_candidates()

    Returns:
    {
        "total": 20,
        "new_applicants": 5,
        "scored": 12,
        "shortlisted": 6,
        "contacted": 4,
        "interview_scheduled": 2,
        "rejected": 1
    }
    """
    if df.empty:
        return {k: 0 for k in [
            "total", "new_applicants", "scored", "shortlisted",
            "contacted", "interview_scheduled", "rejected"
        ]}

    status_col = df["status"].str.strip() if "status" in df.columns else pd.Series(dtype=str)

    scored_mask = pd.to_numeric(df.get("score", pd.Series()), errors="coerce").fillna(0) > 0

    # Use dedicated flag columns — a candidate stays shortlisted/contacted
    # even after their status advances to the next pipeline stage
    shortlisted_col = df["shortlisted"].str.strip().str.lower() if "shortlisted" in df.columns else pd.Series(dtype=str)
    contacted_col   = df["contacted"].str.strip().str.lower()   if "contacted"   in df.columns else pd.Series(dtype=str)

    return {
        "total":               len(df),
        "new_applicants":      int((status_col == "New Applicant").sum()),
        "scored":              int(scored_mask.sum()),
        "shortlisted":         int((shortlisted_col == "yes").sum()),
        "contacted":           int((contacted_col == "yes").sum()),
        "interview_scheduled": int((status_col == "Interview Scheduled").sum()),
        "rejected":            int((status_col == "Rejected").sum())
    }


# ------------------------------------------------------------
# PIPELINE CHART — horizontal bar by stage
# ------------------------------------------------------------

def get_pipeline_chart(df: pd.DataFrame) -> go.Figure:
    """
    Horizontal bar chart showing how many candidates are at each stage.
    Gives the recruiter an instant pipeline health view.
    """
    if df.empty or "status" not in df.columns:
        return _empty_figure("No pipeline data yet")

    counts = df["status"].value_counts().to_dict()

    # Build ordered lists so stages always appear in the same order
    stages = [s for s in STAGE_ORDER if s in counts]
    values = [counts[s] for s in stages]

    # Colour each bar based on stage meaning
    bar_colors = []
    for s in stages:
        if s == "Shortlisted":       bar_colors.append(COLOR_SUCCESS)
        elif s == "Rejected":        bar_colors.append(COLOR_DANGER)
        elif s == "Interview Scheduled": bar_colors.append(COLOR_ELECTRIC)
        elif s == "Contacted":       bar_colors.append(COLOR_GREY_BLUE)
        else:                        bar_colors.append(COLOR_LIGHT_BLUE)

    fig = go.Figure(go.Bar(
        x=values,
        y=stages,
        orientation="h",
        marker_color=bar_colors,
        text=values,
        textposition="outside",
        textfont=dict(color=COLOR_TEXT_DARK, size=12)
    ))

    fig.update_layout(
        **_base_layout("Candidate Pipeline by Stage"),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(
            tickfont=dict(color=COLOR_TEXT_MID, size=11),
            categoryorder="array",
            categoryarray=list(reversed(STAGE_ORDER))
        ),
        height=300,
        margin=dict(l=10, r=40, t=50, b=10)
    )

    return fig


# ------------------------------------------------------------
# SCORE DISTRIBUTION — histogram
# ------------------------------------------------------------

def get_score_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Histogram showing the spread of candidate scores.
    Helps recruiters see at a glance if the talent pool is strong or weak.
    """
    if df.empty or "score" not in df.columns:
        return _empty_figure("No scores yet")

    scores = pd.to_numeric(df["score"], errors="coerce").dropna()
    scores = scores[scores > 0]

    if scores.empty:
        return _empty_figure("Score candidates first")

    fig = go.Figure(go.Histogram(
        x=scores,
        nbinsx=10,
        marker_color=COLOR_ELECTRIC,
        marker_line=dict(color=COLOR_NAVY, width=1),
        opacity=0.85
    ))

    # Add vertical lines for fit thresholds
    fig.add_vline(x=5.0, line_dash="dot", line_color=COLOR_WARNING,
                  annotation_text="Moderate", annotation_font_color=COLOR_WARNING)
    fig.add_vline(x=8.0, line_dash="dot", line_color=COLOR_SUCCESS,
                  annotation_text="Strong", annotation_font_color=COLOR_SUCCESS)

    fig.update_layout(
        **_base_layout("Score Distribution"),
        xaxis=dict(
            title="Score", range=[0, 10],
            tickfont=dict(color=COLOR_TEXT_MID),
            title_font=dict(color=COLOR_MUTED)
        ),
        yaxis=dict(
            title="Candidates",
            tickfont=dict(color=COLOR_TEXT_MID),
            title_font=dict(color=COLOR_MUTED),
            gridcolor="rgba(61,90,128,0.1)"
        ),
        height=300,
        bargap=0.1
    )

    return fig


# ------------------------------------------------------------
# FIT BREAKDOWN — donut chart
# ------------------------------------------------------------

def get_fit_breakdown_chart(df: pd.DataFrame) -> go.Figure:
    """
    Donut chart showing the proportion of Strong / Moderate / Weak fit candidates.
    Clean visual for demo presentations and client dashboards.
    """
    if df.empty or "score_status" not in df.columns:
        return _empty_figure("No fit data yet")

    status_counts = df["score_status"].value_counts()

    labels = []
    values = []
    colors = []

    label_color_map = {
        "Strong Fit":   COLOR_SUCCESS,
        "Moderate Fit": COLOR_WARNING,
        "Weak Fit":     COLOR_DANGER
    }

    for label, color in label_color_map.items():
        if label in status_counts:
            labels.append(label)
            values.append(status_counts[label])
            colors.append(color)

    if not values:
        return _empty_figure("Score candidates first")

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=COLOR_NAVY, width=2)),
        textfont=dict(color=COLOR_WHITE, size=12),
        hovertemplate="%{label}: %{value} candidates<extra></extra>"
    ))

    fig.update_layout(
        **_base_layout("Fit Breakdown"),
        legend=dict(
            font=dict(color=COLOR_TEXT_MID, size=11),
            orientation="v",
            x=1.0, y=0.5
        ),
        height=300,
        margin=dict(l=10, r=80, t=50, b=10)
    )

    return fig


# ------------------------------------------------------------
# RECENT CANDIDATES — activity feed
# ------------------------------------------------------------

def get_recent_candidates(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """
    Returns the N most recently added candidates for the activity feed.
    Sorted by created_at descending.
    """
    if df.empty:
        return pd.DataFrame()

    recent = df.copy()

    if "created_at" in recent.columns:
        recent["created_at"] = pd.to_datetime(recent["created_at"], errors="coerce")
        recent = recent.sort_values("created_at", ascending=False)

    return recent.head(n).reset_index(drop=True)


# ------------------------------------------------------------
# DISPLAY COLUMNS — clean table views
# ------------------------------------------------------------

def get_display_columns(df: pd.DataFrame, view: str = "main") -> pd.DataFrame:
    """
    Returns a cleaned-up subset of columns suitable for display in the UI.

    view options:
        "main"        → Full candidate table
        "shortlisted" → Shortlisted candidates with contact info
        "pipeline"    → Stage tracking view
    """
    if df.empty:
        return df

    column_sets = {
        "main": [
            "candidate_id", "name", "email", "current_role",
            "experience_years", "skills", "score", "score_status", "status"
        ],
        "shortlisted": [
            "candidate_id", "name", "email", "phone",
            "current_role", "score", "score_status", "contacted"
        ],
        "pipeline": [
            "candidate_id", "name", "current_role", "score",
            "status", "interview_date", "interview_time", "interview_stage"
        ]
    }

    cols = column_sets.get(view, column_sets["main"])
    # Only include columns that actually exist in the DataFrame
    available = [c for c in cols if c in df.columns]

    return df[available].copy()


# ------------------------------------------------------------
# SHARED HELPERS
# ------------------------------------------------------------

def _base_layout(title: str) -> dict:
    """Shared Plotly layout — light card background, dark text."""
    return dict(
        title=dict(
            text=title,
            font=dict(color=COLOR_TEXT_DARK, size=13, family="Montserrat"),
            x=0,
            xanchor="left"
        ),
        paper_bgcolor="rgba(0,0,0,0)",   # Transparent — inherits white card background
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLOR_TEXT_MID, family="Montserrat"),
        showlegend=True
    )


def _empty_figure(message: str) -> go.Figure:
    """Returns a blank chart with a centred message when data is missing."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(color=COLOR_MUTED, size=13, family="Montserrat")
    )
    fig.update_layout(
        **_base_layout(""),
        height=300,
        margin=dict(l=10, r=10, t=30, b=10)
    )
    return fig
