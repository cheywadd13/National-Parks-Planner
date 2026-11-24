# Activity-discovery assistant fix

## Cause

The structured model schema had no activity-discovery intent or activity filter. The climbing question was interpreted as unsupported and Python rendered its generic capability message. The retained original browser conversation contains an actual OpenAI response receipt, `resp_02936528dd79f6d6016b0445332cb087d281114616ff4b4bae`. That proves API-backed interpretation occurred, not that the model authored the capability prose.

## Focused change

`src/activities.py` detects climbing, hiking, camping and kayaking requests and matches only reviewed official NPS activity evidence. `src/assistant.py` now exposes a strict activity intent/filter, guards national park scope, retrieves up to three verified options, and supplies official activity links and checked dates. Named-park constraints are honored; discovery-map filters do not silently restrict the assistant. A broad Water activities label does not imply kayaking. Climbing uses explicit climbing/mountaineering evidence rather than canyoneering alone.

Activity records are in the dated NPS profile JSON catalog, not in a claimed Supabase activity table. No schema or database data was changed. A requested month triggers the existing allowlisted read-only Supabase retrieval, with historical weather, visitation, paired-year counts and transparent preference scores. Activity evidence survives unavailable or ineligible historical data. No historical data is fabricated from partial exports.

Missing reviewed records are labeled as missing coverage. Covered records with no verified match are labeled unconfirmed rather than proving no suitable parks exist. Seasonal scores describe historical park-level context, not route access, current weather, permit availability or safety.

## Live API versus fallback

When a key is configured, the normal OpenAI Responses request interprets the question using the expanded schema and its returned response ID/usage is displayed. The validated activity guard corrects unsupported activity interpretations. Python renders factual text from retrieved evidence.

If there is no key or the API fails, recognized activity questions use a deterministic fallback explicitly labeled as **no successful live LLM call**. This label survives chat rerenders. Other requests still require the configured LLM. Mocked provider tests never count as live API verification.

## Verification

- Exact question tested in the running Streamlit UI: Where is a good national park that has climbing activities?
- Ten park records have explicit verified climbing evidence. The unsorted-by-season examples shown are Arches, Black Canyon of the Gunnison and Canyonlands, each with an official climbing guide link.
- With October specified and live read-only history, the current default preference comparison returned Pinnacles, Arches and Zion. Rankings depend on preferences and analysis years; these are not nationwide absolute best claims.
- The exact-question browser test first succeeded through the explicitly labeled fallback. After the key was configured, the exact question was submitted again and succeeded through a real GPT-6 Luna Standard API call: `resp_041594cc611481e6016b0447cfc65087d2bec61c8a4e272133`, completed, 1,243 input and 35 output tokens, interpreted intent activities. The app displayed Arches, Black Canyon of the Gunnison and Canyonlands with official climbing links. Both API and fallback paths were verified; mocked provider tests remain separately identified.
- Full suite: **49 tests, zero failures, errors or skips**, including live read-only checks. `reports/activity_fix_tests.json` and `reports/activity_fix_verification.json` contain results.

## Demo

Open Travel assistant and submit the exact climbing question. Official source links should accompany the park options. For a real API demonstration, enter your key privately in the masked setup field first and confirm that the new response shows a provider response ID. Without that success evidence, describe the result as the deterministic activity fallback. Then ask: Which parks have climbing activities in October? Show the historical source, temperature and park-wide visitor comparison, and explain its limitations.
