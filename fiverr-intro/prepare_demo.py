#!/usr/bin/env python3
"""Prepare HireFlow demo data before screen recording."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(ROOT, ".env"))

from modules.demo_utils import get_sample_cv_files, load_sample_job_description, run_full_client_demo
from modules.sheets_utils import init_sheet


def main() -> int:
    print("Fiverr intro - preparing HireFlow demo...")
    print(f"  Sample CVs: {len(get_sample_cv_files())}")
    print(f"  DEMO_MODE: {os.getenv('DEMO_MODE', 'true')}")

    if not os.path.exists(os.path.join(ROOT, "credentials.json")):
        print("  SKIP: credentials.json missing (use Next.js + samples/QUICK_TEST.md instead)")
        return 0

    init_sheet()
    summary = run_full_client_demo(load_sample_job_description(), top_n=3)
    print(f"  Imported: {summary['imported']}, Scored: {summary['scored']}, Shortlisted: {summary['shortlisted']}")
    if summary["shortlisted_names"]:
        print(f"  Shortlisted: {', '.join(summary['shortlisted_names'])}")
    print("\nReady. Run: streamlit run app.py")
    print("Then record using fiverr-intro/RECORDING_CHECKLIST.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
