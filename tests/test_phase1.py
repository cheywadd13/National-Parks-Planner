"""Phase 1 regression checks. Run python -m unittest discover -s tests -v."""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.database import prepare, read_postgres, COLUMNS
from src.recommendations import suitability, normalize_weights, discovery_candidates, convert_temperature
from src.visualizations import park_map, rank_chart


def history():
    return pd.DataFrame([
        ("TEST", year, month, 20 if month == 1 else 0, 10, 0, 100 if month == 1 else 10)
        for year in range(2020, 2024) for month in range(1, 13)
    ], columns=COLUMNS["weather"] + ["recreation_visits"])


class RecommendationsTests(unittest.TestCase):
    def test_weather_and_crowd_preferences(self):
        rows = history()
        weather = suitability(rows, weather=100, crowds=0)
        crowd = suitability(rows, weather=0, crowds=100)
        self.assertEqual(weather.sort_values("score", ascending=False).iloc[0]["month"], 1)
        self.assertEqual(crowd.loc[crowd.month.eq(1), "crowd_percentile"].iloc[0], 100)
        self.assertTrue(weather.score.between(0, 100).all())
        self.assertEqual(len(weather), 12)

    def test_missing_coverage_and_ties(self):
        rows = history().assign(recreation_visits=0)
        result = suitability(rows)
        self.assertTrue(result.crowd_score.eq(50).all())
        self.assertTrue(suitability(rows, minimum_years=5).score.isna().all())
        missing = rows.assign(total_precip_mm=float("nan"))
        self.assertTrue(suitability(missing).score.isna().all())
        rank_chart(suitability(missing))

    def test_weights_and_units(self):
        self.assertAlmostEqual(normalize_weights(2, 3)[0], .4)
        for weights in [(0, 0), (-1, 1), (float("nan"), 1)]:
            with self.assertRaises(ValueError):
                normalize_weights(*weights)
        self.assertAlmostEqual(convert_temperature(68, "°F", True), 20)
        self.assertAlmostEqual(convert_temperature(20, "°F"), 68)
        with self.assertRaises(ValueError):
            suitability(history(), temperature=(24, 15))

    def test_filters_preserve_reference(self):
        result = suitability(history())
        selected = discovery_candidates(result, 1, (15, 24), 100, 100)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected.iloc[0].crowd_percentile, 100)
        self.assertTrue(discovery_candidates(result, 1, (15, 24), 100, 50).empty)


class DatabaseTests(unittest.TestCase):
    def frames(self):
        rows = history()
        return {
            "parks": pd.DataFrame([["TEST", "Test Park", "CA,NV", 38, -120]], columns=COLUMNS["parks"]),
            "weather": rows[COLUMNS["weather"]],
            "visitation": rows[COLUMNS["visitation"]],
        }

    def test_validation_and_map(self):
        frames = self.frames()
        frames["weather"].loc[0, "total_precip_mm"] = -1
        parks, rows, invalid, orphan = prepare(frames)
        self.assertEqual(invalid, 1)
        self.assertEqual(orphan, 0)
        self.assertEqual(len(rows), 48)
        self.assertTrue(pd.isna(rows.iloc[0].total_precip_mm))
        self.assertEqual(len(park_map(parks, "TEST", "Lower 48").layers[0].data), 1)

    def test_conflicting_keys(self):
        frames = self.frames()
        conflicting = frames["weather"].iloc[[0]].assign(avg_temp_c=99)
        frames["weather"] = pd.concat([frames["weather"], conflicting])
        with self.assertRaises(ValueError):
            prepare(frames)

    def test_read_only_connection(self):
        with patch("psycopg.connect") as connect:
            connection = connect.return_value.__enter__.return_value
            cursor = connection.cursor.return_value.__enter__.return_value
            cursor.fetchall.return_value = []
            read_postgres("postgresql://user:secret@localhost/postgres")
            self.assertTrue(connection.read_only)
            queries = [str(call.args[0]) for call in cursor.execute.call_args_list]
            self.assertEqual(len(queries), 4)
            self.assertIn("SET LOCAL statement_timeout", queries[0])
            self.assertTrue(all("SELECT" in query for query in queries[1:]))


if __name__ == "__main__":
    unittest.main()
