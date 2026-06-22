# ============================================================
# app.py — Acreva HireFlow
# ============================================================
# Entry point. Run with: streamlit run app.py
#
# Layout:
#   Sidebar   → navigation + branding
#   Tab 1     → Dashboard
#   Tab 2     → Candidate Intake (upload + parse CVs)
#   Tab 3     → Scoring (paste JD, score candidates)
#   Tab 4     → Shortlist (auto-shortlist + manage)
#   Tab 5     → Outreach (send emails)
#   Tab 6     → Interview Tracking
# ============================================================

import streamlit as st
import pandas as pd
import os
import datetime
from dotenv import load_dotenv

# ── Module imports ───────────────────────────────────────────
from modules.cv_parser       import process_uploaded_cv
from modules.sheets_utils    import (
    init_sheet, append_candidate, get_all_candidates,
    update_candidate, candidate_exists
)
from modules.scoring_agent   import score_candidate, get_status_from_score
from modules.shortlist_agent import (
    run_auto_shortlist, get_shortlisted_candidates,
    remove_from_shortlist, get_shortlist_summary
)
from modules.outreach_agent  import preview_email, send_outreach
from modules.dashboard_utils import (
    get_kpi_counts, get_pipeline_chart,
    get_score_distribution, get_fit_breakdown_chart,
    get_recent_candidates, get_display_columns
)
from modules.demo_utils import (
    load_sample_job_description, import_sample_candidates,
    score_all_unscored, run_full_client_demo, row_to_scoring_dict
)

load_dotenv()

# ============================================================
# PAGE CONFIG (must be first Streamlit call)
# ============================================================

st.set_page_config(
    page_title="Acreva HireFlow",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# INJECT CSS
# ============================================================

css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ============================================================
# SESSION STATE — persists data within a browser session
# ============================================================

if "parsed_candidates" not in st.session_state:
    st.session_state.parsed_candidates = []   # List of dicts from cv_parser

if "job_description" not in st.session_state:
    st.session_state.job_description = ""

if "sheet_ok" not in st.session_state:
    st.session_state.sheet_ok = False

if "demo_mode" not in st.session_state:
    default_demo = os.getenv("DEMO_MODE", "true").strip().lower() in ("1", "true", "yes")
    st.session_state.demo_mode = default_demo

# ============================================================
# GOOGLE SHEETS — initialise once on startup
# ============================================================

@st.cache_resource(show_spinner=False)
def connect_sheet():
    """Try to connect + initialise the Google Sheet. Cached so it runs once."""
    try:
        msg = init_sheet()
        return True, msg
    except Exception as e:
        return False, str(e)

sheet_ok, sheet_msg = connect_sheet()
st.session_state.sheet_ok = sheet_ok

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("""
    <div style="padding:0.25rem 0.5rem 1.5rem 0.5rem;">
        <div style="font-size:1.35rem; font-weight:800; color:#FFFFFF;
                    letter-spacing:-0.03em; line-height:1.1;">
            Acreva <span style="color:#1A6BFF;">HireFlow</span>
        </div>
        <div style="font-size:0.68rem; color:#7A95BE; margin-top:0.35rem;
                    font-weight:700; letter-spacing:0.09em; text-transform:uppercase;">
            AI Recruitment Assistant
        </div>
        <div style="margin-top:0.85rem; display:inline-block; padding:0.22rem 0.65rem;
                    background:rgba(255,107,43,0.15); border-radius:20px;
                    font-size:0.63rem; color:#FF6B2B; font-weight:700;
                    letter-spacing:0.06em; text-transform:uppercase;
                    border:1px solid rgba(255,107,43,0.25);">
            ● MVP v1.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if sheet_ok:
        st.success("Google Sheets connected", icon="✅")
    else:
        st.error("Sheet not connected", icon="⚠️")
        with st.expander("Setup help"):
            st.markdown("""
            1. Add `credentials.json` to project root
            2. Create sheet: `Acreva_HireFlow_CRM`
            3. Share with service account email
            4. Fill `.env` and restart
            """)

    st.divider()

    st.session_state.demo_mode = st.toggle(
        "Client demo mode",
        value=st.session_state.demo_mode,
        help="When on: emails are preview-only and a demo banner is shown."
    )
    if st.session_state.demo_mode:
        st.info("Demo mode — emails will not be sent.", icon="🎬")

    st.divider()

    if sheet_ok:
        try:
            df_side = get_all_candidates()
            kpis = get_kpi_counts(df_side)
            st.markdown("""
            <div style="font-size:0.65rem; color:#7A95BE; text-transform:uppercase;
                        letter-spacing:0.09em; font-weight:700; margin-bottom:0.85rem;
                        padding:0 0.25rem;">
                Pipeline Stats
            </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            col1.metric("Total",       kpis["total"])
            col2.metric("Shortlisted", kpis["shortlisted"])
            col1.metric("Scored",      kpis["scored"])
            col2.metric("Interviews",  kpis["interview_scheduled"])
        except Exception:
            pass

    st.divider()
    st.markdown("""
    <div style="font-size:0.67rem; color:#4A6FA5; line-height:1.8; padding:0 0.25rem;">
        🤝 AI-assisted scoring only.<br>
        Final hiring decisions remain<br>
        with the recruiter.
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# HEADER BANNER
# ============================================================

st.markdown("""
<div class="hireflow-header">
    <div class="hireflow-header-left">
        <h1>Acreva <span>HireFlow</span></h1>
        <p>AI-Assisted Recruitment — From CV to Shortlist to Interview</p>
    </div>
    <div class="hireflow-header-right">
        <span class="trust-note">🤝 AI-assisted scoring only. Final decision with recruiter.</span>
        <span class="header-badge-orange">🔥 Powered by GPT-4o</span>
    </div>
</div>
""", unsafe_allow_html=True)

if st.session_state.demo_mode:
    st.markdown("""
    <div class="demo-banner">
        <strong>Client demo mode</strong> — safe to present live.
        Use the <strong>Client Demo</strong> tab for a one-click walkthrough.
        Emails are preview-only until you turn demo mode off.
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# MAIN TABS
# ============================================================

tab0, tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🚀 Client Demo",
    "📊 Dashboard",
    "📁 CV Intake",
    "🎯 Scoring",
    "⭐ Shortlist",
    "📧 Outreach",
    "📅 Interviews"
])

# ╔══════════════════════════════════════════════════════════╗
# ║  TAB 0 — CLIENT DEMO                                     ║
# ╚══════════════════════════════════════════════════════════╝

with tab0:
    st.markdown('<div class="section-title">Client <span class="accent">Demo</span></div>',
                unsafe_allow_html=True)

    st.markdown("""
    <div class="section-card demo-steps">
        <div class="section-title">5-minute walkthrough for clients</div>
        <ol>
            <li><strong>Load sample candidates</strong> — 5 realistic CVs</li>
            <li><strong>Score against job</strong> — AI ranks each candidate</li>
            <li><strong>Auto-shortlist</strong> — top matches surfaced instantly</li>
            <li><strong>Preview outreach</strong> — interview invite email (Outreach tab)</li>
            <li><strong>View dashboard</strong> — pipeline charts and KPIs</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    if not sheet_ok:
        st.error("Google Sheets must be connected before running a client demo.")
        st.markdown("""
        **Quick setup:** add `credentials.json`, create sheet `Acreva_HireFlow_CRM`,
        share it with your service account, then restart the app.
        """)
    else:
        demo_col1, demo_col2 = st.columns(2, gap="large")

        with demo_col1:
            st.markdown("**Step-by-step**")
            load_samples_btn = st.button("1. Load sample candidates", use_container_width=True)
            load_jd_btn = st.button("2. Load sample job description", use_container_width=True)
            score_all_btn = st.button("3. Score all candidates", use_container_width=True,
                                      disabled=not st.session_state.job_description)
            shortlist_demo_btn = st.button("4. Shortlist top 3", use_container_width=True)

        with demo_col2:
            st.markdown("**One-click full demo**")
            st.caption("Imports samples, scores everyone, shortlists top 3 — best for live presentations.")
            full_demo_btn = st.button("▶ Run full client demo", type="primary", use_container_width=True)

        if load_jd_btn:
            st.session_state.job_description = load_sample_job_description()
            st.success("Sample job description loaded. Go to Scoring or run step 3.")
            st.rerun()

        if load_samples_btn:
            with st.spinner("Loading sample candidates..."):
                result = import_sample_candidates()
            if result["imported"]:
                st.success(f"Added {result['imported']} candidate(s): {', '.join(result['names'])}")
            if result["skipped"]:
                st.info(f"Skipped {result['skipped']} duplicate(s) already in the sheet.")
            for err in result["errors"]:
                st.warning(err)

        if score_all_btn:
            with st.spinner("Scoring candidates with AI..."):
                result = score_all_unscored(st.session_state.job_description)
            if result["scored"]:
                st.success(f"Scored {result['scored']} candidate(s).")
            else:
                st.info("No unscored candidates left — load samples or upload new CVs.")
            for err in result["errors"]:
                st.warning(err)

        if shortlist_demo_btn:
            with st.spinner("Shortlisting top candidates..."):
                result = run_auto_shortlist(3)
            if result.get("error"):
                st.error(result["error"])
            else:
                st.success(f"Shortlisted {result['count']}: {', '.join(result['shortlisted_names'])}")

        if full_demo_btn:
            jd = load_sample_job_description()
            st.session_state.job_description = jd
            with st.spinner("Running full demo — this takes ~30–60 seconds..."):
                summary = run_full_client_demo(jd, top_n=3)
            st.success(
                f"Demo complete — imported {summary['imported']}, "
                f"scored {summary['scored']}, shortlisted {summary['shortlisted']}."
            )
            if summary["shortlisted_names"]:
                st.markdown("**Shortlisted:** " + ", ".join(summary["shortlisted_names"]))
            st.markdown("👉 Open **Dashboard**, **Outreach**, and **Interviews** tabs to continue the walkthrough.")
            for err in summary["errors"]:
                st.warning(err)

        st.divider()
        st.markdown("**Presentation tips**")
        st.markdown("""
        - Keep **Client demo mode** ON in the sidebar (no accidental emails)
        - Start on this tab, then switch to **Dashboard** to show charts
        - Open **Outreach** to preview an interview invite without sending
        - Mention: *AI assists screening — final hiring decision stays with the recruiter*
        """)

# ╔══════════════════════════════════════════════════════════╗
# ║  TAB 1 — DASHBOARD                                       ║
# ╚══════════════════════════════════════════════════════════╝

with tab1:
    st.markdown('<div class="section-title">Recruitment <span class="accent">Overview</span></div>',
                unsafe_allow_html=True)

    if not sheet_ok:
        st.warning("Connect Google Sheets to see dashboard data.")
    else:
        try:
            df = get_all_candidates()
            kpis = get_kpi_counts(df)

            # ── KPI Cards ───────────────────────────────────
            st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
            kpi_cols = st.columns(7)
            kpi_items = [
                ("Total Candidates", kpis["total"],               "",        "👥"),
                ("New Applicants",   kpis["new_applicants"],      "",        "📥"),
                ("Scored",           kpis["scored"],              "",        "🎯"),
                ("Shortlisted",      kpis["shortlisted"],         "success", "⭐"),
                ("Contacted",        kpis["contacted"],           "orange",  "📧"),
                ("Interviews",       kpis["interview_scheduled"], "warning", "📅"),
                ("Rejected",         kpis["rejected"],            "danger",  "✕"),
            ]
            for col, (label, value, variant, icon) in zip(kpi_cols, kpi_items):
                with col:
                    st.markdown(f"""
                    <div class="kpi-card {variant}">
                        <span class="kpi-icon">{icon}</span>
                        <div class="kpi-number">{value}</div>
                        <div class="kpi-label">{label}</div>
                    </div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Charts row ──────────────────────────────────
            ch1, ch2, ch3 = st.columns(3)
            with ch1:
                st.plotly_chart(get_pipeline_chart(df),
                                use_container_width=True, config={"displayModeBar": False})
            with ch2:
                st.plotly_chart(get_score_distribution(df),
                                use_container_width=True, config={"displayModeBar": False})
            with ch3:
                st.plotly_chart(get_fit_breakdown_chart(df),
                                use_container_width=True, config={"displayModeBar": False})

            # ── Recent candidates ────────────────────────────
            st.markdown('<div class="section-title" style="margin-top:1.5rem;">Recent <span class="accent">Activity</span></div>',
                        unsafe_allow_html=True)

            recent = get_recent_candidates(df, n=8)
            if recent.empty:
                st.info("No candidates yet. Upload CVs in the CV Intake tab.")
            else:
                display = get_display_columns(recent, "main")
                st.dataframe(display, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Could not load dashboard: {e}")

# ╔══════════════════════════════════════════════════════════╗
# ║  TAB 2 — CV INTAKE                                       ║
# ╚══════════════════════════════════════════════════════════╝

with tab2:
    st.markdown('<div class="section-title">Upload & <span class="accent">Parse CVs</span></div>',
                unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        job_title_input = st.text_input(
            "Job Title (optional)",
            placeholder="e.g. Sales Executive, Marketing Manager"
        )

        uploaded_files = st.file_uploader(
            "Upload CVs (PDF, DOCX, or TXT)",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=True,
            help="Upload one or more candidate CVs at once"
        )

        parse_btn = st.button("Parse CVs", use_container_width=True)

    with col_right:
        st.markdown("""
        <div class="section-card" style="margin-top:0;">
            <div class="section-title">How It Works</div>
            <ol style="color:#94A3B8; font-size:0.85rem; line-height:2;">
                <li>Upload one or multiple CV files</li>
                <li>Optionally enter the job title</li>
                <li>Click <strong style="color:#fff;">Parse CVs</strong></li>
                <li>AI extracts candidate details</li>
                <li>Records are saved to Google Sheets</li>
            </ol>
            <div style="font-size:0.78rem; color:#4A6FA5; margin-top:0.75rem;">
                Supported: PDF · Word (.docx) · Plain text (.txt)
            </div>
        </div>
        """, unsafe_allow_html=True)

    if parse_btn:
        if not uploaded_files:
            st.warning("Please upload at least one CV file.")
        elif not sheet_ok:
            st.error("Google Sheets is not connected. Cannot save candidates.")
        else:
            new_parsed = []
            progress = st.progress(0, text="Parsing CVs...")

            for i, file in enumerate(uploaded_files):
                progress.progress(
                    int((i / len(uploaded_files)) * 100),
                    text=f"Parsing {file.name}..."
                )
                with st.spinner(f"Reading {file.name}..."):
                    candidate = process_uploaded_cv(file)

                    # Skip duplicates
                    if candidate_exists(candidate.get("email", "")):
                        st.warning(f"**{file.name}** — Candidate already exists in sheet. Skipped.")
                        continue

                    # Save to Google Sheets
                    candidate_id = append_candidate(candidate, job_title_input)
                    candidate["candidate_id"] = candidate_id

                    new_parsed.append(candidate)

            progress.progress(100, text="Done!")

            if new_parsed:
                st.session_state.parsed_candidates.extend(new_parsed)
                st.success(f"✅ {len(new_parsed)} candidate(s) parsed and saved to Google Sheets.")

    # ── Show parsed results ──────────────────────────────────
    if st.session_state.parsed_candidates:
        st.markdown('<div class="section-title" style="margin-top:1.5rem;">Parsed <span class="accent">Candidates</span></div>',
                    unsafe_allow_html=True)

        display_data = []
        for c in st.session_state.parsed_candidates:
            display_data.append({
                "ID":          c.get("candidate_id", "—"),
                "Name":        c.get("name", "Unknown"),
                "Email":       c.get("email", "—"),
                "Current Role": c.get("current_role", "—"),
                "Skills":      c.get("skills", "—")[:60] + "..." if len(c.get("skills","")) > 60 else c.get("skills","—"),
                "Exp (yrs)":   c.get("experience_years", "—"),
                "File":        c.get("filename", "—")
            })

        st.dataframe(pd.DataFrame(display_data), use_container_width=True, hide_index=True)

    elif not parse_btn:
        # Show candidates already in sheet
        if sheet_ok:
            try:
                existing = get_all_candidates()
                if not existing.empty:
                    st.markdown('<div class="section-title" style="margin-top:1.5rem;">All <span class="accent">Candidates in Sheet</span></div>',
                                unsafe_allow_html=True)
                    st.dataframe(
                        get_display_columns(existing, "main"),
                        use_container_width=True, hide_index=True
                    )
            except Exception:
                pass

# ╔══════════════════════════════════════════════════════════╗
# ║  TAB 3 — SCORING                                         ║
# ╚══════════════════════════════════════════════════════════╝

with tab3:
    st.markdown('<div class="section-title">Candidate <span class="accent">Scoring</span></div>',
                unsafe_allow_html=True)

    # ── Job description input ────────────────────────────────
    jd_text = st.text_area(
        "Paste Job Description",
        value=st.session_state.job_description,
        height=200,
        placeholder="Paste the full job description here. Include required skills, experience, and responsibilities."
    )
    if jd_text:
        st.session_state.job_description = jd_text

    # Load sample JD button
    sample_path = os.path.join(os.path.dirname(__file__), "data", "sample_job_description.txt")
    if os.path.exists(sample_path):
        if st.button("Load Sample Job Description", use_container_width=False):
            with open(sample_path) as f:
                st.session_state.job_description = f.read()
            st.rerun()

    st.divider()

    # ── Candidate selection ──────────────────────────────────
    if not sheet_ok:
        st.warning("Connect Google Sheets to load candidates for scoring.")
    else:
        try:
            df_all = get_all_candidates()

            if df_all.empty:
                st.info("No candidates found. Upload CVs in the CV Intake tab first.")
            else:
                # Show only unscored candidates
                unscored_mask = pd.to_numeric(df_all.get("score", pd.Series()), errors="coerce").isna() | \
                                (pd.to_numeric(df_all.get("score", pd.Series()), errors="coerce") == 0)
                unscored_df = df_all[unscored_mask]

                st.markdown(f"""
                <div style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">
                    {len(unscored_df)} unscored candidate(s) ready · {len(df_all) - len(unscored_df)} already scored
                </div>
                """, unsafe_allow_html=True)

                score_col1, score_col2 = st.columns([2, 1])

                with score_col1:
                    score_mode = st.radio(
                        "Score candidates",
                        ["Score all unscored candidates", "Score a specific candidate"],
                        horizontal=True
                    )

                with score_col2:
                    score_btn = st.button("Run Scoring", use_container_width=True,
                                          disabled=not st.session_state.job_description)

                if not st.session_state.job_description:
                    st.caption("⚠️ Paste a job description above before scoring.")

                # Single candidate picker
                selected_candidate_id = None
                if score_mode == "Score a specific candidate":
                    name_options = df_all[["candidate_id", "name"]].apply(
                        lambda r: f"{r['name']} ({r['candidate_id']})", axis=1
                    ).tolist()
                    selected_label = st.selectbox("Select candidate", name_options)
                    if selected_label:
                        selected_candidate_id = selected_label.split("(")[-1].rstrip(")")

                # ── Run scoring ──────────────────────────────
                if score_btn and st.session_state.job_description:

                    if score_mode == "Score all unscored candidates":
                        candidates_to_score = unscored_df.to_dict("records")
                    else:
                        candidates_to_score = df_all[
                            df_all["candidate_id"] == selected_candidate_id
                        ].to_dict("records")

                    if not candidates_to_score:
                        st.info("No candidates to score.")
                    else:
                        progress_s = st.progress(0, text="Scoring candidates...")
                        results_display = []

                        for i, row in enumerate(candidates_to_score):
                            progress_s.progress(
                                int((i / len(candidates_to_score)) * 100),
                                text=f"Scoring {row.get('name', 'candidate')}..."
                            )

                            # Build candidate dict expected by scoring_agent
                            candidate_dict = row_to_scoring_dict(row)

                            result = score_candidate(candidate_dict, st.session_state.job_description)

                            # Save score back to Google Sheets
                            update_candidate(row["candidate_id"], {
                                "score":        result["score"],
                                "score_status": result["status"],
                                "score_reason": " | ".join(result.get("reason", [])),
                                "status":       "Scored"
                            })

                            results_display.append({
                                "Name":    row.get("name", "Unknown"),
                                "Score":   f"{result['score']} / 10",
                                "Status":  result["status"],
                                "Reasons": " · ".join(result.get("reason", []))[:120]
                            })

                        progress_s.progress(100, text="Scoring complete!")
                        st.success(f"✅ Scored {len(results_display)} candidate(s).")
                        st.dataframe(pd.DataFrame(results_display),
                                     use_container_width=True, hide_index=True)

                # ── Scored candidates table ──────────────────
                scored_df = df_all[pd.to_numeric(df_all.get("score", pd.Series()), errors="coerce") > 0]
                if not scored_df.empty:
                    st.markdown('<div class="section-title" style="margin-top:1.5rem;">Scored <span class="accent">Results</span></div>',
                                unsafe_allow_html=True)
                    view_cols = ["name", "current_role", "score", "score_status", "score_reason"]
                    available = [c for c in view_cols if c in scored_df.columns]
                    st.dataframe(scored_df[available].sort_values("score", ascending=False),
                                 use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Scoring error: {e}")

# ╔══════════════════════════════════════════════════════════╗
# ║  TAB 4 — SHORTLIST                                       ║
# ╚══════════════════════════════════════════════════════════╝

with tab4:
    st.markdown('<div class="section-title">Auto <span class="accent">Shortlist</span></div>',
                unsafe_allow_html=True)

    if not sheet_ok:
        st.warning("Connect Google Sheets to use this feature.")
    else:
        sh_col1, sh_col2 = st.columns([1, 2], gap="large")

        with sh_col1:
            st.markdown("""
            <div class="section-card" style="margin-top:0;">
                <div class="section-title">How Shortlisting Works</div>
                <p style="color:#94A3B8; font-size:0.85rem; line-height:1.8;">
                    The system sorts all scored candidates by their AI score
                    and automatically marks the top N as <strong style="color:#22C55E;">Shortlisted</strong>.
                    You remain in control — you can remove any candidate from
                    the shortlist at any time.
                </p>
            </div>
            """, unsafe_allow_html=True)

            top_n = st.slider("Number of candidates to shortlist", 1, 20, 5)

            shortlist_btn = st.button("⭐ Auto Shortlist Top Candidates",
                                      use_container_width=True)

        with sh_col2:
            if shortlist_btn:
                with st.spinner("Shortlisting top candidates..."):
                    result = run_auto_shortlist(top_n)

                if result["error"]:
                    st.error(result["error"])
                else:
                    st.success(f"✅ {result['count']} candidates shortlisted!")
                    for name in result["shortlisted_names"]:
                        st.markdown(f"- ⭐ **{name}**")

            # ── Shortlisted candidates table ─────────────────
            try:
                shortlisted_df = get_shortlisted_candidates()

                if shortlisted_df.empty:
                    st.info("No shortlisted candidates yet. Run Auto Shortlist first.")
                else:
                    st.markdown(f"""
                    <div style="font-size:0.85rem; color:#94A3B8; margin-bottom:1rem;">
                        {len(shortlisted_df)} shortlisted candidate(s)
                    </div>
                    """, unsafe_allow_html=True)

                    display = get_display_columns(shortlisted_df, "shortlisted")
                    st.dataframe(display, use_container_width=True, hide_index=True)

                    # ── Remove from shortlist ─────────────────
                    st.markdown("---")
                    st.markdown("**Remove from shortlist**")
                    remove_options = shortlisted_df.apply(
                        lambda r: f"{r['name']} ({r['candidate_id']})", axis=1
                    ).tolist()
                    remove_select = st.selectbox("Select candidate to remove", ["— select —"] + remove_options)

                    if st.button("Remove from Shortlist") and remove_select != "— select —":
                        cid = remove_select.split("(")[-1].rstrip(")")
                        if remove_from_shortlist(cid):
                            st.success("Candidate removed from shortlist.")
                            st.rerun()

            except Exception as e:
                st.error(f"Could not load shortlisted candidates: {e}")

# ╔══════════════════════════════════════════════════════════╗
# ║  TAB 5 — OUTREACH                                        ║
# ╚══════════════════════════════════════════════════════════╝

with tab5:
    st.markdown('<div class="section-title">Candidate <span class="accent">Outreach</span></div>',
                unsafe_allow_html=True)

    if st.session_state.demo_mode:
        st.info("Demo mode is ON — you can preview emails safely. Nothing will be sent.", icon="🎬")

    if not sheet_ok:
        st.warning("Connect Google Sheets to use outreach.")
    else:
        try:
            shortlisted_df = get_shortlisted_candidates()

            if shortlisted_df.empty:
                st.info("Shortlist candidates first before sending outreach emails.")
            else:
                out_col1, out_col2 = st.columns([1, 1], gap="large")

                with out_col1:
                    # ── Email settings ───────────────────────
                    email_type = st.selectbox(
                        "Email Type",
                        ["interview_invite", "follow_up", "acknowledgement"],
                        format_func=lambda x: {
                            "interview_invite": "Interview Invitation",
                            "follow_up":        "Follow Up",
                            "acknowledgement":  "Application Acknowledgement"
                        }[x]
                    )

                    company_name   = st.text_input("Company Name",   placeholder="e.g. Acreva Technologies")
                    recruiter_name = st.text_input("Your Name",      placeholder="e.g. Sarah Johnson")
                    jd_for_email   = st.text_input("Job Title",      placeholder="e.g. Sales Executive")

                    interview_date   = ""
                    interview_time   = ""
                    interview_format = ""
                    if email_type == "interview_invite":
                        picked_date      = st.date_input("Interview Date", value=datetime.date.today() + datetime.timedelta(days=3))
                        interview_date   = picked_date.strftime("%A %d %B %Y")
                        time_options     = [
                            "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
                            "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
                            "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM",
                            "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM",
                            "05:00 PM",
                        ]
                        interview_time   = st.selectbox("Interview Time", time_options, index=2)
                        interview_format = st.text_input("Format", value="Video call (link to follow)")

                    # ── Candidate selector ───────────────────
                    cand_options = shortlisted_df.apply(
                        lambda r: f"{r['name']} — {r.get('email','no email')} ({r['candidate_id']})",
                        axis=1
                    ).tolist()
                    selected_cand = st.selectbox("Select Candidate", cand_options)

                with out_col2:
                    # ── Email preview ────────────────────────
                    if selected_cand:
                        cand_id_sel = selected_cand.split("(")[-1].rstrip(")")
                        cand_row = shortlisted_df[
                            shortlisted_df["candidate_id"] == cand_id_sel
                        ].iloc[0].to_dict()

                        preview = preview_email(
                            email_type=email_type,
                            candidate=cand_row,
                            job_title=jd_for_email or cand_row.get("job_title", "the role"),
                            company_name=company_name or "our company",
                            recruiter_name=recruiter_name or "The Recruitment Team",
                            interview_date=interview_date,
                            interview_time=interview_time,
                            interview_format=interview_format or "Video call (link to follow)"
                        )

                        st.markdown("**Email Preview**")

                        editable_subject = st.text_input("Subject", value=preview["subject"])
                        editable_body    = st.text_area("Body",     value=preview["body"], height=280)

                        recipient_email  = cand_row.get("email", "")
                        st.caption(f"Sending to: **{recipient_email}**")

                        # ── Confirm send ─────────────────────
                        confirm = st.checkbox("I have reviewed this email and it is ready to send")
                        send_btn = st.button("Send Email", disabled=not confirm,
                                             use_container_width=True)

                        if send_btn and confirm:
                            if st.session_state.demo_mode:
                                st.success(
                                    f"Demo mode — email preview only. Would send to **{recipient_email}**. "
                                    "Turn off Client demo mode in the sidebar to send for real."
                                )
                            else:
                                with st.spinner("Sending email..."):
                                    result = send_outreach(
                                        candidate_id=cand_id_sel,
                                        candidate_email=recipient_email,
                                        subject=editable_subject,
                                        body=editable_body
                                    )

                                if result["success"]:
                                    st.success(f"✅ Email sent to {recipient_email}")
                                else:
                                    st.error(f"Failed: {result['error']}")

        except Exception as e:
            st.error(f"Outreach error: {e}")

# ╔══════════════════════════════════════════════════════════╗
# ║  TAB 6 — INTERVIEW TRACKING                              ║
# ╚══════════════════════════════════════════════════════════╝

with tab6:
    st.markdown('<div class="section-title">Interview <span class="accent">Tracking</span></div>',
                unsafe_allow_html=True)

    if not sheet_ok:
        st.warning("Connect Google Sheets to use interview tracking.")
    else:
        try:
            df_all = get_all_candidates()

            if df_all.empty:
                st.info("No candidates in the system yet.")
            else:
                tr_col1, tr_col2 = st.columns([1, 1], gap="large")

                with tr_col1:
                    st.markdown("**Update Candidate Stage**")

                    # Candidate selector
                    cand_labels = df_all.apply(
                        lambda r: f"{r['name']} ({r['candidate_id']})", axis=1
                    ).tolist()
                    selected_tr = st.selectbox("Select Candidate", cand_labels, key="track_select")

                    cand_id_tr = selected_tr.split("(")[-1].rstrip(")")
                    cand_data  = df_all[df_all["candidate_id"] == cand_id_tr].iloc[0]

                    new_status = st.selectbox(
                        "Status",
                        ["New Applicant", "Scored", "Shortlisted", "Contacted",
                         "Interview Scheduled", "Rejected"],
                        index=["New Applicant", "Scored", "Shortlisted", "Contacted",
                               "Interview Scheduled", "Rejected"].index(
                            cand_data.get("status", "New Applicant")
                        ) if cand_data.get("status") in
                            ["New Applicant","Scored","Shortlisted","Contacted",
                             "Interview Scheduled","Rejected"] else 0
                    )

                    existing_date = cand_data.get("interview_date", "")
                    try:
                        default_date = datetime.datetime.strptime(existing_date, "%A %d %B %Y").date() if existing_date else datetime.date.today() + datetime.timedelta(days=3)
                    except Exception:
                        default_date = datetime.date.today() + datetime.timedelta(days=3)
                    picked_date_tr    = st.date_input("Interview Date", value=default_date, key="interview_date_picker")
                    interview_date_tr = picked_date_tr.strftime("%A %d %B %Y")

                    time_options_tr = [
                        "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
                        "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
                        "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM",
                        "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM",
                        "05:00 PM",
                    ]
                    existing_time = cand_data.get("interview_time", "10:00 AM")
                    time_idx = time_options_tr.index(existing_time) if existing_time in time_options_tr else 2
                    interview_time_tr = st.selectbox("Interview Time", time_options_tr, index=time_idx, key="interview_time_picker")
                    interview_stage_tr = st.selectbox(
                        "Interview Stage",
                        ["—", "First Interview", "Second Interview", "Final Interview", "Offer Made"],
                        index=0
                    )
                    notes_tr = st.text_area("Notes", value=cand_data.get("notes", ""), height=100)

                    update_btn = st.button("Update Record", use_container_width=True)

                    if update_btn:
                        updates = {
                            "status":          new_status,
                            "interview_date":  interview_date_tr,
                            "interview_time":  interview_time_tr,
                            "notes":           notes_tr
                        }
                        if interview_stage_tr != "—":
                            updates["interview_stage"] = interview_stage_tr

                        update_candidate(cand_id_tr, updates)
                        st.success(f"✅ {cand_data['name']}'s record updated.")
                        st.rerun()

                with tr_col2:
                    # ── Pipeline table ───────────────────────
                    st.markdown("**Full Pipeline View**")
                    pipeline = get_display_columns(df_all, "pipeline")
                    st.dataframe(
                        pipeline.sort_values("status") if "status" in pipeline.columns else pipeline,
                        use_container_width=True,
                        hide_index=True
                    )

        except Exception as e:
            st.error(f"Interview tracking error: {e}")
