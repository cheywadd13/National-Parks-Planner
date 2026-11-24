"""Deterministic local staging and read-only change planning."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd

from ..database import COLUMNS, KEY
from .extract import capture_bytes, write_immutable
from .transform import parks_from_metadata, visitation_from_nps, combine_seki, weather_from_monthly


def plan_changes(incoming, current, keys):
    incoming = incoming.set_index(keys).sort_index()
    current = current.set_index(keys).sort_index()
    new = incoming.index.difference(current.index)
    shared = incoming.index.intersection(current.index)
    equal = incoming.loc[shared].eq(current.loc[shared]) | (
        incoming.loc[shared].isna() & current.loc[shared].isna())
    changed = equal.all(axis=1).eq(False)
    return {"new_rows": len(new), "unchanged_rows": int((~changed).sum()),
            "conflicting_existing_rows": int(changed.sum()),
            "existing_only_rows": len(current.index.difference(incoming.index))}


def stage(metadata_path, visitation_path, weather_path, output_directory):
    inputs = {"metadata": Path(metadata_path), "visitation": Path(visitation_path),
              "weather": Path(weather_path)}
    directory = Path(output_directory)
    provenance = {}
    for name, path in inputs.items():
        content = path.read_bytes()
        archived = capture_bytes(content, directory / "raw", path.suffix)
        provenance[name] = {"filename": path.name, "sha256": sha256(content).hexdigest(),
                            "archived_file": archived.name}
    parks = parks_from_metadata(pd.read_csv(inputs["metadata"]))
    visits = combine_seki(visitation_from_nps(pd.read_csv(inputs["visitation"], dtype=str)))
    weather = weather_from_monthly(pd.read_csv(inputs["weather"]))
    frames = {"parks": parks, "visitation": visits, "weather": weather}
    for name in ["visitation", "weather"]:
        unknown = set(frames[name]["park_code"]) - set(parks["park_code"])
        if unknown:
            raise ValueError(f"Unmapped source codes in {name}: {sorted(unknown)}")
    encoded = {f"{name}_supabase.csv": frame[COLUMNS[name]].to_csv(index=False, lineterminator="\n").encode()
               for name, frame in frames.items()}
    identity_content = b"".join(name.encode() + data for name, data in sorted(encoded.items()))
    identity_content += json.dumps(provenance, sort_keys=True).encode() + b"transform-v2"
    identity = sha256(identity_content).hexdigest()
    destination = directory / identity
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"transformation_version": 2, "run_id": identity, "source_files": provenance,
                "rows": {name: len(frame) for name, frame in frames.items()},
                "outputs": {name: sha256(data).hexdigest() for name, data in encoded.items()},
                "seki": "SEQU + KICA visitation; weather retained at one point",
                "database_writes": 0}
    encoded["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True).encode()
    for name, content in encoded.items():
        write_immutable(destination / name, content)
    return destination, frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--visitation", required=True)
    parser.add_argument("--weather-monthly", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--compare-live", action="store_true",
                        help="Read DATABASE_URL and report changes without loading")
    args = parser.parse_args()
    destination, frames = stage(args.metadata, args.visitation, args.weather_monthly, args.output)
    print(destination)
    if args.compare_live:
        import os
        from ..database import read_postgres
        current = read_postgres(os.environ["DATABASE_URL"])
        report = {name: plan_changes(frame, current[name], ["park_code"] if name=="parks" else KEY)
                  for name, frame in frames.items()}
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
