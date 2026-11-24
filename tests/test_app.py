"""Run UI regressions against PARKS_CSV_DIR when local exports are available."""

import os
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.getenv("PARKS_CSV_DIR"), "Set PARKS_CSV_DIR for UI integration tests")
class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45).run()
        self.assert_healthy()

    def assert_healthy(self):
        self.assertFalse(self.app.exception, [str(value) for value in self.app.exception])
        self.assertFalse(self.app.error, [str(value) for value in self.app.error])
        self.assertTrue(self.app.radio)

    def test_all_pages(self):
        for page in ["Visit rankings", "Compare", "Data & methods", "Explore", "Travel assistant"]:
            with self.subTest(page=page):
                self.app.radio(key="page").set_value(page).run()
                self.assert_healthy()

    def test_units_and_discovery(self):
        self.app.radio(key="page").set_value("Explore").run()
        next(widget for widget in self.app.radio if widget.label == "Temperature units").set_value("°F").run()
        self.assert_healthy()
        next(widget for widget in self.app.checkbox if widget.label == "Apply historical climate and crowd limits").check().run()
        self.assert_healthy()
        next(widget for widget in self.app.selectbox if widget.label == "Preferred travel month").set_value(10).run()
        self.assert_healthy()
        self.app.text_input[0].set_value("no such national park").run()
        self.assertTrue(self.app.info)
        self.assertFalse(self.app.exception)

    def test_zero_weights(self):
        next(widget for widget in self.app.slider if widget.label == "Weather importance").set_value(0)
        next(widget for widget in self.app.slider if widget.label == "Avoiding crowds importance").set_value(0)
        self.app.run()
        self.assertTrue(self.app.warning)
        self.assertFalse(self.app.exception)

    def test_activity_filter_recovery(self):
        self.app.text_input[0].set_value("yellowstone")
        next(x for x in self.app.selectbox if x.label == "State or territory").set_value("WY")
        self.app.multiselect(key="activity_choices").set_value(["Hiking", "Climbing", "Camping"])
        self.app.run()
        self.assert_healthy()
        self.assertTrue(any(x.value == "Yellowstone National Park" for x in self.app.header))
        next(x for x in self.app.radio if x.label == "Match selected activities").set_value("All selected activities").run()
        self.assertTrue(any("saved official activity listings" in x.value for x in self.app.info))
        next(x for x in self.app.button if x.label == "Clear activity filters").click().run()
        self.assert_healthy()

    def test_assistant_conversation_with_mocked_provider(self):
        query = dict(intent="park_info", park_codes=["ACAD"], months=[10], difficulty="Any", temperature_c=None)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-placeholder"}), \
             patch("src.assistant_ui.interpret", return_value=(query, {"input_tokens": 100, "output_tokens": 20})) as router:
            self.app.radio(key="page").set_value("Travel assistant").run()
            self.app.chat_input[0].set_value("Tell me about Acadia").run()
            self.assert_healthy()
            self.assertEqual(self.app.session_state["travel_plan"]["months"], [10])
            self.assertEqual(self.app.session_state["travel_calls"], 1)
            self.assertTrue(any("Confirmed activity listings" in x.value for x in self.app.markdown))
            router.return_value = (dict(query, intent="quiet_parks", park_codes=[]), {})
            self.app.chat_input[0].set_value("Fewest visitors in October?").run()
            self.assert_healthy()
            self.assertTrue(any("Connect live Supabase" in x.value for x in self.app.markdown))

    def test_activity_fallback_in_ui_with_missing_key(self):
        from src.assistant import AssistantUnavailable
        with patch("src.assistant_ui.interpret", side_effect=AssistantUnavailable("API unavailable")):
            self.app.radio(key="page").set_value("Travel assistant").run()
            self.app.chat_input[0].set_value("Where is a good national park that has climbing activities?").run()
            self.assert_healthy()
            text=" ".join(m.value for m in self.app.markdown)
            self.assertIn("Arches National Park",text)
            self.assertIn("Black Canyon",text)
            self.assertIn("Canyonlands National Park",text)
            self.assertTrue(any("Deterministic activity fallback" in x.value for x in self.app.info))
            self.assertFalse(any("Real OpenAI API interpretation verified" in x.value for x in self.app.success))
            self.app.run()
            self.assertTrue(any("Deterministic activity fallback" in x.value for x in self.app.caption))

    def test_session_key_survives_page_navigation(self):
        self.app.radio(key="page").set_value("Travel assistant").run()
        self.app.text_input(key="temporary_openai_key").set_value("unit-test-placeholder").run()
        self.assertEqual(self.app.session_state["_travel_api_key"],"unit-test-placeholder")
        self.app.radio(key="page").set_value("Explore").run()
        self.app.radio(key="page").set_value("Travel assistant").run()
        self.assertEqual(self.app.text_input(key="temporary_openai_key").value,"unit-test-placeholder")
        self.assert_healthy()
