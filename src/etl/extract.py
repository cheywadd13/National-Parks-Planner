"""Immutable raw capture with checksums, unit metadata, and bounded HTTP retries."""

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
import time
from tempfile import NamedTemporaryFile
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def read_published(path):
    """Allow a bounded transient sharing violation after Windows publication."""
    for attempt in range(5):
        try:
            return path.read_bytes()
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.02 * (2 ** attempt))


def write_immutable(path, content):
    """Publish complete content atomically without replacing an existing file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=path.parent, prefix=".staging-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        try:
            if os.name == "nt":
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
        except FileExistsError:
            if read_published(path) != content:
                raise ValueError(f"Immutable artifact differs: {path.name}")
    finally:
        temporary.unlink(missing_ok=True)
    return path


def capture_bytes(content, directory, suffix):
    return write_immutable(Path(directory) / f"{sha256(content).hexdigest()}{suffix}", content)


def session():
    client = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"], respect_retry_after_header=True)
    client.mount("https://", HTTPAdapter(max_retries=retry))
    return client


def request_snapshot(client, url, parameters, raw_directory, headers=None):
    # Manifests retain safe request parameters. API keys enter only through headers.
    response = client.get(url, params=parameters, headers=headers, timeout=(10, 120))
    response.raise_for_status()
    payload = response.json()
    record = {"url": url, "parameters": parameters, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
              "payload": payload}
    encoded = json.dumps(record, sort_keys=True, allow_nan=False).encode()
    path = capture_bytes(encoded, raw_directory, ".json")
    return payload, path


def collect_park_metadata(raw_directory, client=None):
    api_key = os.environ.get("NPS_API_KEY")
    if not api_key:
        raise ValueError("Set NPS_API_KEY for fresh NPS metadata collection")
    client = client or session()
    records, files = [], []
    start = 0
    while True:
        payload, path = request_snapshot(
            client, "https://developer.nps.gov/api/v1/parks",
            {"limit": 100, "start": start}, raw_directory, {"X-Api-Key": api_key})
        batch = payload["data"]
        records.extend(batch)
        files.append(str(path))
        start += len(batch)
        if start >= int(payload["total"]):
            break
        if not batch:
            raise ValueError("NPS pagination stopped before the reported total")
    designations = {"National Park", "National Park & Preserve", "National Parks"}
    selected = [row for row in records if row.get("designation") in designations
                or row["parkCode"].lower() in {"npsa", "redw"}]
    return selected, files


def collect_weather(park, start_date, end_date, raw_directory, client=None):
    from datetime import date
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if start > end or start.day != 1:
        raise ValueError("Use an ordered date range beginning on the first of a month")
    from calendar import monthrange
    if end.day != monthrange(end.year, end.month)[1]:
        raise ValueError("End the weather range on the final day of a month")
    return request_snapshot(
        client or session(), "https://archive-api.open-meteo.com/v1/archive",
        {"latitude": float(park["latitude"]), "longitude": float(park["longitude"]),
         "start_date": start_date, "end_date": end_date,
         "daily": "temperature_2m_mean,precipitation_sum,snowfall_sum",
         "temperature_unit": "celsius", "precipitation_unit": "mm", "timezone": "auto"},
        raw_directory)
