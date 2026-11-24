"""Refresh the bundled official NPS page snapshots without database writes."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd
import requests

from ..nps_api import checked_now, decode_html, parse_public_profile, parse_public_activities
from .extract import capture_bytes


def collect_one(park, raw_directory):
    code = park["park_code"].lower()
    home = f"https://www.nps.gov/{code}/index.htm"
    url = f"https://www.nps.gov/{code}/planyourvisit/things2do.htm"
    profile, evidence = {}, []
    for kind, address in [("home", home), ("activities", url)]:
        response = requests.get(address, timeout=(10, 30))
        response.raise_for_status()
        raw = capture_bytes(response.content, raw_directory, ".html")
        evidence.append({"kind": kind, "url": address, "sha256": sha256(response.content).hexdigest(),
                         "raw_file": raw.name})
        html = decode_html(response.content)
        if kind == "home":
            profile = parse_public_profile(html, code, home, checked_now())
            profile["park_name"] = park["park_name"]
        else:
            profile["activities"] = parse_public_activities(html, code, url)
    profile["evidence"] = evidence
    return profile


def collect(inventory, output, raw_directory):
    parks = pd.read_csv(inventory).to_dict("records")
    profiles, errors = {}, {}
    def attempt(park):
        try:
            return park["park_code"], collect_one(park, raw_directory), None
        except (requests.RequestException, ValueError, KeyError) as error:
            return park["park_code"], None, type(error).__name__
    with ThreadPoolExecutor(max_workers=4) as pool:
        for code, record, error in pool.map(attempt, parks):
            if record:
                profiles[code] = record
            else:
                errors[code] = error
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {"schema_version": 1, "checked_at": checked_now(), "profiles": profiles, "errors": errors}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"profiles": len(profiles), "errors": errors,
                      "with_images": sum(bool(p["images"]) for p in profiles.values()),
                      "with_activities": sum(bool(p["activities"]) for p in profiles.values())}))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--output", default="data/park_profiles.json")
    parser.add_argument("--raw-directory", default="reports/park_content_raw")
    args = parser.parse_args()
    collect(args.inventory, args.output, args.raw_directory)
