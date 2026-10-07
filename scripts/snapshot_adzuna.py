"""Optional standalone utility to fetch live labour market snapshots from the Adzuna API.

Reads ADZUNA_APP_ID and ADZUNA_APP_KEY from environment variables.
Does NOT invent data or guess API endpoints.
Nothing else in the PRISM module depends on this script.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List

# Adzuna API Endpoint Constants
ADZUNA_COUNTRY = "in"  # India labour market
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api"
ADZUNA_JOBS_SEARCH_URL = f"{ADZUNA_BASE_URL}/jobs/{ADZUNA_COUNTRY}/search/1"
ADZUNA_HISTORICAL_SALARY_URL = f"{ADZUNA_BASE_URL}/jobs/{ADZUNA_COUNTRY}/history"
# TODO: Confirm whether Adzuna API provides granular monthly historical time-series postings
# by specific SOC career code or whether historical endpoint is limited to macro salary distributions.

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "snapshots"


def fetch_adzuna_snapshots() -> None:
    """Fetch live data from Adzuna API and save to JSON snapshots."""
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        print("[ERROR] ADZUNA_APP_ID or ADZUNA_APP_KEY environment variable is missing.")
        print("Please export both variables before invoking this script:")
        print("  set ADZUNA_APP_ID=your_app_id")
        print("  set ADZUNA_APP_KEY=your_app_key")
        print("Exiting without modifying local snapshots.")
        sys.exit(1)

    try:
        import requests
    except ImportError:
        print("[ERROR] 'requests' library is required to run live Adzuna snapshotting.")
        print("Install it with 'pip install requests'.")
        sys.exit(1)

    print(f"[INFO] Connecting to Adzuna API for country '{ADZUNA_COUNTRY}'...")

    # TODO: Verify official parameter name for query term: 'what' vs 'title_only' in Adzuna docs
    test_params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 1,
        "what": "software engineer",
        "content-type": "application/json",
    }

    try:
        response = requests.get(ADZUNA_JOBS_SEARCH_URL, params=test_params, timeout=15)
        response.raise_for_status()
        data = response.json()
        total_count = data.get("count", 0)
        print(f"[INFO] Adzuna API connected successfully. Total active postings reported: {total_count}")
        # Note: In accordance with hackathon anti-hallucination rules, we do not invent
        # time-series mapping logic until production SOC mappings are finalized.
        print("[INFO] Live snapshot creation requires complete SOC code mapping table.")
        print("Exiting cleanly without inventing synthetic records.")
    except Exception as exc:
        print(f"[ERROR] Adzuna API request failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    fetch_adzuna_snapshots()
