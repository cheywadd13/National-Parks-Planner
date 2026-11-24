"""Programming requirements: genuine transformations and bounded LLM behavior."""

import json
from hashlib import sha256
from pathlib import Path
import unittest
import tempfile
from unittest.mock import Mock, MagicMock, patch

import pandas as pd
import requests
from src.assistant import interpret, validate_plan, retrieve, fact_text, AssistantUnavailable, check_model_access, DEFAULT_MODEL, record_api_receipt, enforce_named_park_scope
from src.travel_queries import historical_rows, evidence_rows
from src.eda import diagnostics, findings
from src.nps_api import official_url, api_records, normalize_api_profile
from src.trails import load_trails, filter_trails, search_trails, difficulty_matches
from src.etl.collect_verified_trails import collect, watchman_record
from src.database import COLUMNS
from src.etl.extract import read_published


def plan(intent="quiet_parks", codes=None, months=None):
    return dict(intent=intent, park_codes=codes or [], months=months or [10], difficulty="Any", temperature_c=None)


def fixtures():
    parks = pd.DataFrame([{"park_code": "YELL", "park_name": "Yellowstone"},
                          {"park_code": "ZION", "park_name": "Zion"}])
    history = pd.DataFrame([(code, year, month, 18, 10, 0, visits)
                            for code, visits in [("YELL", 200), ("ZION", 100)]
                            for year in range(2020, 2024) for month in range(1, 13)],
                           columns=COLUMNS["weather"] + ["recreation_visits"])
    prefs = dict(temperature=[15, 24], weather=65, crowds=35, minimum_years=3, years=[2020, 2023])
    return parks, history, prefs


class AssistantTests(unittest.TestCase):
    def test_national_scope_cannot_be_silently_restricted(self):
        parks, _, _ = fixtures()
        p = plan("quiet_parks", ["YELL", "ZION"], [10])
        self.assertEqual(enforce_named_park_scope(p, "Which parks have the fewest visits in October?", parks)["park_codes"], [])
        fixed = enforce_named_park_scope(plan("hikes", ["YELL"], [10]),
                    "I'm visiting Zion National Park in October. Based on historical weather and crowds, would you recommend visiting then? What moderate hikes could I do, and why?", parks)
        self.assertEqual(fixed["park_codes"], ["ZION"])
        self.assertEqual(fixed["intent"], "visit_and_hikes")
        timing_first = enforce_named_park_scope(plan("best_months", ["ZION"], [10]),
                          "Zion in October: what weather and moderate hikes should I expect?", parks)
        self.assertEqual(timing_first["intent"], "visit_and_hikes")

    def test_strict_plan_and_injection(self):
        validate_plan(plan(), {"YELL"})
        for bad in [dict(plan(), park_codes=["YELL'; DROP TABLE parks;--"]),
                    dict(plan(), months=[True]), dict(plan(), months=[13]),
                    dict(plan(), temperature_c=[float("nan"), 20]), dict(plan(), temperature_c=[30, 10]),
                    dict(plan(), sql="DELETE FROM parks"), dict(plan(), intent="write")]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_plan(bad, {"YELL"})

    def test_real_provider_contract_mocked(self):
        parks, _, prefs = fixtures()
        client = Mock()
        client.post.return_value.json.return_value = {
            "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(plan())}]}],
            "usage": {"input_tokens": 100, "output_tokens": 40}}
        result, usage = interpret("Fewest visitors in October?", parks, plan(months=[9]), prefs, "test-key", session=client,
                                  evidence_refs=[{"park_code": "YELL", "month": 9}])
        self.assertEqual(result["months"], [10])
        args = client.post.call_args.kwargs
        self.assertFalse(args["json"]["store"])
        self.assertEqual(args["json"]["model"], "gpt-6-luna")
        self.assertEqual(args["json"]["service_tier"], "default")
        self.assertEqual(args["json"]["reasoning"], {"effort": "none"})
        self.assertEqual(args["json"]["max_output_tokens"], 384)
        self.assertNotIn("test-key", json.dumps(args["json"]))
        self.assertEqual(args["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(args["json"]["text"]["format"]["type"], "json_schema")
        self.assertEqual(usage["input_tokens"], 100)
        self.assertEqual(json.loads(args["json"]["input"])["previous_results"], [{"park_code": "YELL", "month": 9}])

    def test_api_failure_and_missing_key(self):
        parks, _, prefs = fixtures()
        with self.assertRaises(AssistantUnavailable):
            interpret("Hi", parks, None, prefs, None)
        client = Mock()
        client.post.side_effect = requests.Timeout("secret details")
        with self.assertRaises(AssistantUnavailable) as caught:
            interpret("Hi", parks, None, prefs, "key", session=client)
        self.assertNotIn("secret details", str(caught.exception))
        client.post.side_effect = None
        client.post.return_value.json.return_value = {"status": "incomplete"}
        with self.assertRaises(AssistantUnavailable):
            interpret("Hi", parks, None, prefs, "key", session=client)

    def test_model_account_check_does_not_generate_tokens(self):
        client = Mock()
        client.get.return_value.status_code = 200
        client.get.return_value.json.return_value = {"id": DEFAULT_MODEL}
        self.assertEqual(check_model_access("key", session=client)["status"], "listed")
        client.post.assert_not_called()
        client.get.return_value.status_code = 404
        self.assertEqual(check_model_access("key", session=client)["status"], "unavailable")
        client.get.side_effect = requests.Timeout()
        self.assertEqual(check_model_access("key", session=client)["status"], "unknown")

    def test_fixed_sql_bound_parameters(self):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []
        with patch("src.travel_queries.open_readonly", return_value=connection):
            historical_rows("private-dsn", 2005, 2025, "YELL")
        query, parameters = cursor.execute.call_args.args
        self.assertIn("%s", query)
        self.assertNotIn("YELL", query)
        self.assertEqual(parameters, (2005, 2025, "YELL", "YELL"))
        with self.assertRaises(ValueError):
            historical_rows("private-dsn", 2025, 2005)

    def test_absolute_crowd_rank_and_missingness(self):
        parks, history, prefs = fixtures()
        result = evidence_rows(history, parks, plan(), prefs)
        self.assertEqual(result[0]["park_code"], "ZION")
        self.assertEqual(result[0]["recreation_visits"], 100)
        self.assertEqual(result[0]["years"], 4)
        self.assertEqual(result[0]["crowd_percentile"], 50)
        history.loc[history.park_code.eq("ZION"), "recreation_visits"] = float("nan")
        result = evidence_rows(history, parks, plan(), prefs)
        self.assertEqual([x["park_code"] for x in result], ["YELL"])

    def test_live_retrieval_uses_allowlist_and_preserves_years(self):
        parks, history, prefs = fixtures()
        with patch("src.assistant.historical_rows", return_value=history) as get:
            packet = retrieve(plan(codes=["YELL"]), parks, prefs, {}, None, dsn="secret")
        get.assert_called_once_with("secret", 2020, 2023, "YELL")
        self.assertEqual(packet["years"], [2020, 2023])
        self.assertNotIn("secret", fact_text(packet))

    def test_unknown_hikes_and_alerts_are_not_invented(self):
        parks, history, prefs = fixtures()
        p = plan("hikes", ["ZION"])
        p["difficulty"] = "Strenuous"
        packet = retrieve(p, parks, prefs, {}, None, local_history=history)
        self.assertEqual(packet["rows"], [])
        self.assertIn("No matching trails", fact_text(packet))
        packet = retrieve(plan("alerts", ["YELL"]), parks, prefs, {},
                          lambda code: {"status": "unavailable", "alerts": [], "checked_at": None})
        self.assertIn("current NPS alerts unavailable", fact_text(packet))
        self.assertNotIn("returned no alerts", fact_text(packet))

    def test_combined_question_keeps_weather_when_trails_missing(self):
        parks, history, prefs = fixtures()
        p = plan("visit_and_hikes", ["ZION"], [10])
        p["difficulty"] = "Moderate"
        packet = retrieve(p, parks, prefs, {}, None, local_history=history)
        self.assertEqual(packet["historical"]["rows"][0]["month"], 10)
        self.assertEqual(packet["trails"]["rows"][0]["name"], "Watchman Trail")
        self.assertIn("Historical visit recommendation", fact_text(packet))
        self.assertIn("inside your 15", fact_text(packet))
        with patch("src.assistant.load_trails", return_value=[]):
            packet = retrieve(p, parks, prefs, {}, None, local_history=history)
        self.assertTrue(packet["historical"]["rows"])
        self.assertIn("No trail data available", fact_text(packet))

    def test_missing_coverage_and_filter_exclusion_are_distinct(self):
        catalog = load_trails()
        missing = search_trails(catalog, ["OLYM"], "Moderate")
        excluded = search_trails(catalog, ["ACAD"], "Moderate")
        self.assertEqual(missing["coverage"][0]["status"], "no_data")
        self.assertEqual(excluded["coverage"][0]["status"], "no_matches")
        self.assertIn("No trail data available", fact_text(missing))
        self.assertIn("No matching trails", fact_text(excluded))
        self.assertTrue(filter_trails(catalog, " zion ", "moderate"))
        self.assertTrue(difficulty_matches("Easy to Moderate", "Moderate"))
        self.assertFalse(difficulty_matches(None, "Moderate"))

    def test_api_receipt_excludes_keys_and_questions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"receipt.jsonl"
            data = {"id": "resp_fixture", "status": "completed", "model": "gpt-6-luna", "service_tier": "default",
                    "usage": {"input_tokens": 100, "output_tokens": 30}, "api_key": "private-key", "question": "private-question"}
            self.assertTrue(record_api_receipt(data, "visit_and_hikes", path))
            stored = path.read_text(encoding="utf-8")
            self.assertNotIn("private-key", stored)
            self.assertNotIn("private-question", stored)
            self.assertEqual(json.loads(stored)["response_id"], "resp_fixture")

    def test_month_score_explanation(self):
        parks, history, prefs = fixtures()
        packet = retrieve(plan("compare_months", ["YELL"], [7, 9]), parks, prefs, {}, None, local_history=history)
        self.assertEqual(len(packet["rows"]), 2)
        self.assertIn("0.0 points above", fact_text(packet))
        self.assertIn("not a prediction", fact_text(packet))


class EDATests(unittest.TestCase):
    def test_seasonal_flags_retain_rows_and_show_sensitivity(self):
        _, history, _ = fixtures()
        rows = history.loc[(history.park_code == "YELL") & (history.month == 1)].iloc[[0]*10].copy()
        rows["year"] = range(2010, 2020)
        rows["recreation_visits"] = [98, 99, 100, 100, 101, 101, 102, 103, 104, 10000]
        rows.iloc[0, rows.columns.get_loc("avg_temp_c")] = float("nan")
        before = rows.copy(deep=True)
        report = diagnostics(rows).set_index("metric")
        self.assertEqual(report.loc["recreation_visits", "flagged"], 1)
        self.assertEqual(report.loc["avg_temp_c", "missing"], 1)
        self.assertGreater(report.loc["recreation_visits", "mean_all"], report.loc["recreation_visits", "mean_without_flags"])
        pd.testing.assert_frame_equal(rows, before)
        self.assertEqual(diagnostics(rows.iloc[:3])["screened"].sum(), 0)
        self.assertIn("Highest observed", findings(rows)[0])


class ContentTests(unittest.TestCase):
    def test_provenance_and_unknown_details(self):
        trails = load_trails()
        self.assertEqual(len(trails), 17)
        self.assertEqual(len({r["park_code"] for r in trails}), 6)
        self.assertTrue(all(official_url(r["source_url"]) for r in trails))
        fairy = next(r for r in trails if "Fairy" in r["name"])
        self.assertIsNone(fairy["elevation_ft"])
        parus = next(r for r in trails if "rus" in r["name"])
        self.assertIsNone(parus["distance_miles"])
        self.assertNotIn(parus, filter_trails(trails, "ZION", include_unknown=False))
        root = Path(__file__).resolve().parents[1]
        profiles = json.loads((root/"data/park_profiles.json").read_text(encoding="utf-8"))["profiles"]
        self.assertEqual(len(profiles), 63)
        self.assertTrue(all(official_url(r["official_url"]) for r in profiles.values()))
        self.assertGreaterEqual(sum(bool(r["description"]) for r in profiles.values()), 61)
        for record in trails:
            self.assertEqual(sha256((root/"reports/trail_content_raw"/record["raw_file"]).read_bytes()).hexdigest(), record["sha256"])
        for profile in profiles.values():
            for evidence in profile["evidence"]:
                self.assertEqual(sha256((root/"reports/park_content_raw"/evidence["raw_file"]).read_bytes()).hexdigest(), evidence["sha256"])

    def test_verified_watchman_etl_is_locally_idempotent(self):
        root = Path(__file__).resolve().parents[1]
        trail = next(r for r in load_trails() if r["trail_id"] == "ZION-watchman")
        content = (root/"reports/trail_content_raw"/trail["raw_file"]).read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target/"data").mkdir()
            (target/"data/trails.json").write_bytes((root/"data/trails.json").read_bytes())
            response = Mock(content=content, text=content.decode("utf-8"))
            with patch("src.etl.collect_verified_trails.requests.get", return_value=response):
                collect(target)
                collect(target)
            rows = json.loads((target/"data/trails.json").read_text(encoding="utf-8"))["trails"]
            self.assertEqual(len(rows), 17)
            self.assertEqual(sum(r["trail_id"] == "ZION-watchman" for r in rows), 1)
            self.assertEqual(trail["distance_miles"], 3.3)
            self.assertEqual(trail["difficulty"], "Moderate")
            self.assertIsNone(trail["elevation_ft"])
        with self.assertRaises(ValueError):
            watchman_record("Unverified content", "date", "digest", "raw")

    def test_nps_pagination_and_safe_urls(self):
        with patch.object(Path, "read_bytes", side_effect=[PermissionError("sharing"), b"raw"]):
            self.assertEqual(read_published(Path("fixture")), b"raw")
        self.assertIsNone(official_url(None))
        self.assertIsNone(official_url("https://nps.gov.attacker.test/x"))
        self.assertIsNone(official_url("javascript:alert(1)"))
        client = Mock()
        a, b = Mock(), Mock()
        a.json.return_value = {"data": [{"id": "first"}], "total": "2"}
        b.json.return_value = {"data": [{"id": "second"}], "total": "2"}
        client.get.side_effect = [a, b]
        self.assertEqual(len(api_records("alerts", "YELL", "key", client)), 2)
        self.assertEqual(client.get.call_args.kwargs["params"]["start"], 1)
        self.assertNotIn("key", client.get.call_args.kwargs["params"])
        with self.assertRaises(ValueError):
            api_records("delete", "YELL", "key")


if __name__ == "__main__":
    unittest.main()
