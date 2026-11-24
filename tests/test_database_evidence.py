"""Optional integration checks against live PostgreSQL without any data writes."""

import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.audit import query_frame, compare_numeric
from src.database import open_readonly, read_tables, prepare
from src.recommendations import suitability

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.getenv("RUN_LIVE_DB_TESTS") == "1" and os.getenv("DATABASE_URL"),
                     "Set RUN_LIVE_DB_TESTS=1 and DATABASE_URL for read-only integration tests")
class LiveDatabaseEvidenceTests(unittest.TestCase):
    def test_sql_python_preference_parity(self):
        with open_readonly(os.environ["DATABASE_URL"]) as connection:
            _, rows, _, _ = prepare(read_tables(connection))
            query = (ROOT/"sql/05_suitability.sql").read_text(encoding="utf-8")
            for low, high, weather, crowds, minimum in [
                (15, 24, 65, 35, 3), (-5, 0, 0, 100, 3), (10, 22, 100, 0, 21), (10, 22, 1, 1, 22)
            ]:
                with self.subTest(preferences=(low, high, weather, crowds, minimum)):
                    expected = suitability(rows, (low, high), weather, crowds, minimum)
                    with connection.cursor() as cursor:
                        actual = query_frame(cursor, query, dict(
                            start_year=2005, end_year=2025, temp_low=low, temp_high=high,
                            weather_weight=weather, crowd_weight=crowds, minimum_years=minimum))
                    compared = compare_numeric(expected, actual, ["park_code","month"],
                                                ["score","crowd_percentile","rank","years"])
                    self.assertEqual(compared["mismatching_rows"], 0)

    def test_live_app_and_chart_inputs(self):
        with patch.dict(os.environ, {"PARKS_CSV_DIR": ""}):
            # Any accidental CSV fallback fails this test immediately.
            with patch("src.database.read_csv_directory", side_effect=AssertionError("Unexpected CSV fallback")):
                app = AppTest.from_file(str(ROOT/"app.py"), default_timeout=45).run()
                self.assertFalse(app.exception, [str(x) for x in app.exception])
                self.assertFalse(app.error)
                self.assertTrue(any("live Supabase PostgreSQL" in item.value for item in app.caption))
                chart = json.loads(app.get("plotly_chart")[0].proto.spec)
                self.assertEqual(len(chart["data"]), 1)
                for page in ["Visit rankings","Compare","Data & methods"]:
                    app.radio(key="page").set_value(page).run()
                    self.assertFalse(app.exception, [str(x) for x in app.exception])
                    self.assertFalse(app.error)
