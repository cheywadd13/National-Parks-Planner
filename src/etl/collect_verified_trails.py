"""Review-gated NPS trail ingestion to a local catalog; no database writes."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from .extract import capture_bytes

WATCHMAN_URL = "https://www.nps.gov/thingstodo/hike-watchman-trail.htm"


def watchman_record(html, checked_at, digest, raw_file):
    """Require the reviewed source statements; changed facts trigger review."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("#main") or soup
    text = " ".join(main.get_text(" ", strip=True).split())
    required = [r"Zion National Park", r"Watchman Trail", r"moderate out-and-back",
                r"3\.3 miles", r"roundtrip", r"1[-–]2 Hours", r"Bikes are not permitted",
                r"Pets Allowed No", r"Reservations No", r"Year Round", r"muddy or icy", r"Limited shade"]
    if not all(re.search(pattern, text, re.I) for pattern in required):
        raise ValueError("Watchman source changed; review the official page before updating the catalog")
    return {"trail_id": "ZION-watchman", "park_code": "ZION", "name": "Watchman Trail",
            "source_url": WATCHMAN_URL, "distance_miles": 3.3, "distance_basis": "round trip",
            "difficulty": "Moderate", "elevation_ft": None, "elevation_kind": "Full-route elevation gain",
            "duration": "1–2 hours",
            "trailhead": "Zion Canyon Visitor Center: follow the plaza sidewalk past the shuttle stop to the crosswalk, then follow the river to the trail.",
            "description": "Climb from the river to an overlook of the Watchman, lower Zion Canyon, sandstone towers and Springdale.",
            "season_note": "NPS lists year-round use, with potential muddy or icy conditions in winter and monsoon season and limited summer shade. This is general guidance, not a current condition report.",
            "restrictions": "NPS prohibits bikes and pets. The route has sandy, rocky, uneven surfaces and drop-offs.",
            "measurement_note": "The 3.3-mile distance describes the published round trip. NPS accessibility data gives separate overlook and loop segments; a full-route total elevation gain is not reported and is not inferred by summing segments.",
            "permit_note": "NPS lists no reservations, but this does not establish all permit or current access requirements. Park entrance fees apply; check official guidance.",
            "checked_at": checked_at, "sha256": digest, "raw_file": raw_file,
            "source_title": "Watchman Trail (U.S. National Park Service)"}


def collect(directory=None):
    root = Path(directory) if directory else Path(__file__).resolve().parents[2]
    response = requests.get(WATCHMAN_URL, timeout=(5, 20))
    response.raise_for_status()
    digest = sha256(response.content).hexdigest()
    raw = capture_bytes(response.content, root/"reports/trail_content_raw", ".html")
    record = watchman_record(response.text, datetime.now(timezone.utc).isoformat(), digest, raw.name)
    path = root/"data/trails.json"
    catalog = json.loads(path.read_text(encoding="utf-8"))
    # Stable source identity replaces its own local snapshot; never appends a duplicate.
    catalog["trails"] = [r for r in catalog["trails"] if r["trail_id"] != record["trail_id"]] + [record]
    path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    return {"source_url": WATCHMAN_URL, "trail_id": record["trail_id"], "catalog_records": len(catalog["trails"]),
            "database_writes": 0, "source_sha256": digest}


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2))
