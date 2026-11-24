"""ETL regressions target missing-day bias, identity mapping, and idempotency."""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import pandas as pd

from src.etl.extract import capture_bytes
from src.etl.pipeline import stage, plan_changes
from src.etl.transform import (
    weather_from_daily, visitation_from_nps, combine_seki, parks_from_metadata,
)


def daily_payload():
    dates = pd.date_range("2020-02-01", "2020-02-29")
    return {"daily_units": {"temperature_2m_mean": "°C", "precipitation_sum": "mm",
                             "snowfall_sum": "cm"},
            "daily": {"time": dates.strftime("%Y-%m-%d").tolist(),
                      "temperature_2m_mean": list(range(29)),
                      "precipitation_sum": [2]*29, "snowfall_sum": [0.5]*29}}


class EtlTests(unittest.TestCase):
    def test_concurrent_immutable_capture(self):
        with TemporaryDirectory() as directory:
            with ThreadPoolExecutor(max_workers=4) as workers:
                files = list(workers.map(lambda _: capture_bytes(b"same raw payload", directory, ".json"),
                                         range(8)))
            self.assertEqual(len(set(files)), 1)
            self.assertEqual(files[0].read_bytes(), b"same raw payload")

    def test_full_leap_month_aggregation(self):
        row = weather_from_daily(daily_payload(), "TEST").iloc[0]
        self.assertEqual(row.avg_temp_c, 14)
        self.assertEqual(row.total_precip_mm, 58)
        self.assertEqual(row.total_snowfall_cm, 14.5)

    def test_daily_missing_duplicate_and_units_fail(self):
        for scenario in ["missing", "duplicate", "null", "units"]:
            with self.subTest(scenario=scenario):
                payload = daily_payload()
                if scenario == "missing":
                    for values in payload["daily"].values():
                        values.pop()
                elif scenario == "duplicate":
                    payload["daily"]["time"][0] = payload["daily"]["time"][1]
                elif scenario == "null":
                    payload["daily"]["precipitation_sum"][0] = None
                else:
                    payload["daily_units"]["snowfall_sum"] = "mm"
                with self.assertRaises(ValueError):
                    weather_from_daily(payload, "TEST")

    def test_missing_entire_month_fails(self):
        dates = pd.date_range("2020-01-01", "2020-03-31")
        dates = dates[dates.month != 2]
        payload = daily_payload()
        payload["daily"] = {
            "time": dates.strftime("%Y-%m-%d").tolist(),
            "temperature_2m_mean": [10]*len(dates),
            "precipitation_sum": [0]*len(dates),
            "snowfall_sum": [0]*len(dates),
        }
        with self.assertRaises(ValueError):
            weather_from_daily(payload, "TEST")

    def test_seki_requires_both_components(self):
        raw = pd.DataFrame({"UnitCode": ["SEQU", "KICA"], "Year": [2020, 2020],
                            "Month": [1, 1], "RecreationVisits": ["1,000", "200"]})
        visits = visitation_from_nps(raw)
        combined = combine_seki(visits)
        self.assertEqual(combined.iloc[0].recreation_visits, 1200)
        self.assertEqual(combined.iloc[0].park_code, "SEKI")
        with self.assertRaises(ValueError):
            combine_seki(visits.iloc[:1])
        with self.assertRaises(ValueError):
            visitation_from_nps(pd.concat([raw, raw.iloc[[0]].assign(RecreationVisits="99")]))

    def test_count_validation(self):
        for invalid in ["-1", "1.5", "", "NaN"]:
            with self.subTest(invalid=invalid):
                raw = pd.DataFrame({"UnitCode": ["TEST"], "Year": [2020], "Month": [1],
                                    "RecreationVisits": [invalid]})
                with self.assertRaises(ValueError):
                    visitation_from_nps(raw)

    def test_immutable_capture_and_staging(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            metadata = pd.DataFrame({"parkCode": ["seki"], "fullName": ["Sequoia and Kings Canyon"],
                                     "states": ["CA"], "latitude": [36.7], "longitude": [-118.8]})
            visitation = pd.DataFrame({"UnitCode": ["SEQU", "KICA"], "Year": [2020, 2020],
                                       "Month": [1, 1], "RecreationVisits": [100, 200]})
            weather = pd.DataFrame({"park_code": ["SEKI"], "year": [2020], "month": [1],
                                    "avg_temp_c": [4], "total_precip_mm": [20],
                                    "total_snowfall_cm": [5]})
            paths = []
            for name, frame in [("metadata", metadata), ("visitation", visitation), ("weather", weather)]:
                path = base/f"{name}.csv"
                frame.to_csv(path, index=False)
                paths.append(path)
            first, frames = stage(*paths, base/"staging")
            bytes_before = {path.name: path.read_bytes() for path in first.iterdir()}
            second, _ = stage(*paths, base/"staging")
            self.assertEqual(first, second)
            self.assertEqual(len(pd.read_csv(first/"visitation_supabase.csv")), 1)
            self.assertEqual(bytes_before, {path.name: path.read_bytes() for path in second.iterdir()})
            self.assertEqual(json.loads((first/"manifest.json").read_text())["database_writes"], 0)
            changes = plan_changes(frames["visitation"], frames["visitation"], ["park_code","year","month"])
            self.assertEqual(changes["new_rows"], 0)
            self.assertEqual(changes["unchanged_rows"], 1)
            changed = frames["visitation"].assign(recreation_visits=1)
            self.assertEqual(plan_changes(changed, frames["visitation"], ["park_code","year","month"])["conflicting_existing_rows"], 1)
