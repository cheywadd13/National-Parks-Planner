# Programming final speaker notes

Planned talk plus live demo: approximately 13 minutes. Reserve the remaining time for questions.

## Slide 1

TIME: 30 seconds
SAY:
National Parks Explorer turns historical weather, recreation visitation, and verified park information into a practical travel-planning application. This is my solo Programming for Data Science final. I will show the acquisition pipeline, EDA, application, and a real API-backed language interface, then demonstrate the app.
SOURCES:
https://www.nps.gov/yell/index.htm
https://www.nps.gov/common/uploads/structured_data/2815637A-9869-FC9C-99461D0B36AA1922.jpg?maxWidth=1200&maxHeight=800&quality=90
https://www.nps.gov/aboutus/disclaimer.htm

## Slide 2

TIME: 40 seconds
SAY:
The problem is fragmented planning information. Visitors need to understand both what a park offers and how seasons change its weather and visitor patterns. This actual screenshot shows the destination guide. The application combines discovery, verified activities, transparent seasonal scoring, comparisons, and an optional language assistant. The inventory contains 63 reporting records; it is not a claim about 63 distinct officially designated parks.
SOURCES:
Read-only Supabase data, 2005–2025. Evidence: reports/final_release_tests.json; reports/trail_fix_live_verification.json; presentation source_data.json.
Actual application screenshot: docs/screenshots/park-guide.jpg

## Slide 3

TIME: 55 seconds
SAY:
Python retrieves external data and preserves raw source snapshots with provenance and hashes. The NPS API supplies official metadata and optional current alerts, while the visitation collection uses NPS monthly recreation records. Open-Meteo supplies daily historical temperature, precipitation, and snowfall, transformed to monthly summaries. I reran acquisition for Acadia 2025: 365 daily observations produced 12 monthly aggregates matching stored values within tolerance. Existing historical notebook and R collection work is documented. Live database writes were not needed for release verification. Alerts require an NPS key and are not claimed to have been retrieved in this release.
SOURCES:
https://www.nps.gov/subjects/developer/api-documentation.htm
https://irma.nps.gov/Stats/
https://open-meteo.com/en/docs/historical-weather-api
reports/programming_api_acquisition/
docs/etl_lineage.md

## Slide 4

TIME: 60 seconds
SAY:
Missing data is treated explicitly. The 13 absent visitation months remain absent rather than becoming zero visits. Invalid or nonfinite numeric values are handled without erasing legitimate zero rainfall or snowfall. The outlier screen uses Tukey 1.5 IQR within each park and calendar month, requiring at least eight years and a positive IQR. Here Yellowstone flags seven temperatures, six precipitation values, eight snowfall values, and three visitation values. These are screening flags, not proof of error, so the default analysis retains them. Temperature, rain, and visits each have 252 screened records. Snow has 210 screened; 42 zero-IQR cases are unscreened. The interface compares results with and without flags.
SOURCES:
Read-only Supabase data, 2005–2025. Evidence: reports/final_release_tests.json; reports/trail_fix_live_verification.json; presentation source_data.json.
src/eda.py; tests/test_programming.py; source_data.json yellowstone_diagnostics

## Slide 5

TIME: 55 seconds
SAY:
This editable chart uses a fresh read-only extraction of Yellowstone monthly records from 2005 through 2025. Each bar is the mean for that calendar month across years. July averages 896,346 recreation visits, compared with 16,475 in November. These are recreation entries, not unique individuals and not measurements of crowding on a particular trail. The large seasonal range motivates month selection, but lower visitation alone does not establish that winter access or conditions are suitable.
SOURCES:
Read-only Supabase data, 2005–2025. Evidence: reports/final_release_tests.json; reports/trail_fix_live_verification.json; presentation source_data.json.
source_data.json yellowstone_monthly; src/eda.py

## Slide 6

TIME: 60 seconds
SAY:
Raw Spearman correlation between Yellowstone temperature and visitation is about 0.855. After subtracting each variable’s calendar-month mean, the Spearman association falls to about 0.074. Both calculations have 252 paired observations. Raw precipitation correlation is minus 0.375 and snowfall minus 0.795; the adjusted values are minus 0.076 and minus 0.180. This suggests much of the raw association reflects the seasonal cycle. It does not prove that weather has no influence, nor establish causality. Month demeaning also does not remove all year trends, access effects, or special events.
SOURCES:
Read-only Supabase data, 2005–2025. Evidence: reports/final_release_tests.json; reports/trail_fix_live_verification.json; presentation source_data.json.
source_data.json yellowstone_associations; src/eda.py

## Slide 7

TIME: 55 seconds
SAY:
This is an actual screenshot of the Yellowstone EDA page. Descriptive statistics, seasonal charts, missingness, outlier sensitivity, and correlations are presented within the application. Other working views include the interactive discovery map, park guides, visit rankings, and comparison for two or three parks. Users can adjust year coverage, temperature comfort, and the balance between weather and avoiding crowds. Recommendation scores are transparent preference-based summaries of historical observations. They are not forecasts or trail safety assessments.
SOURCES:
Read-only Supabase data, 2005–2025. Evidence: reports/final_release_tests.json; reports/trail_fix_live_verification.json; presentation source_data.json.
Actual screenshot: docs/screenshots/eda-yellowstone.jpg; app.py; src/visualizations.py

## Slide 8

TIME: 60 seconds
SAY:
The LLM is integrated through an actual OpenAI Responses API request. Its meaningful role is turning a natural-language question into a constrained structured intent, including park, month, difficulty, and preferences. Python validates that plan, executes predefined read-only parameterized queries, and renders calculated facts and citations. The LLM does not produce arbitrary SQL or author the factual statistics. GPT-6 Luna uses default service tier, which is Standard processing, with a 384 output-token limit and no automatic paid retry or fallback. The key can be entered in a masked session-only setup field. Without a key, the rest of the app still works. The image is the configuration screen, not a claimed chat-response screenshot.
SOURCES:
src/assistant.py; src/travel_queries.py; reports/openai_verification.json
Actual screenshot: docs/screenshots/assistant-configuration.jpg
https://platform.openai.com/docs/api-reference/responses

## Slide 9

TIME: 65 seconds
SAY:
This exact mixed question was verified after correcting the compound-intent bug. October ranks first out of twelve for Zion with the default 65 percent weather and 35 percent crowd weighting and a 15 to 24 Celsius preferred range. The score is 76.87. The historical monthly median temperature is 11.44 Celsius, so I explicitly explain that it is cooler than the preferred range. Median visitation is 314,966 and the within-park crowd percentile is 45.45, using 21 paired years. The reviewed Watchman Trail is officially Moderate, 3.3 miles round trip, with a published duration of one to two hours. Total elevation gain is unreported and is not invented. The successful corrected API call has a durable provider response ID and 1,086 input and 37 output tokens; the user also confirmed it worked. This slide is a verified evidence summary rather than a fabricated chat screenshot. Monthly averages do not indicate current trail conditions. Check official access and permit information before departure.
SOURCES:
Read-only Supabase data, 2005–2025. Evidence: reports/final_release_tests.json; reports/trail_fix_live_verification.json; presentation source_data.json.
reports/openai_verification.json
Provider response: resp_091180e458086bf9016b03c1a4809087d2a01e3be52edc4527
https://www.nps.gov/thingstodo/hike-watchman-trail.htm
https://www.nps.gov/zion/index.htm
https://www.nps.gov/common/uploads/structured_data/68BFC1AC-BF96-629F-89D261D78F181C64.jpg?maxWidth=1200&maxHeight=800&quality=90

## Slide 10

TIME: 45 seconds
SAY:
The full final release suite passed 38 tests with no failures, errors, or skipped tests, including two live read-only Supabase checks. Tests cover transformations, recommendations, joins, assistant routing, missing trail information, and Streamlit behavior. Code is separated into acquisition, analysis, query, content, visualization, and assistant modules. External requests use timeouts and graceful failures. This was a solo project with AI-assisted development, not a claim of teammate contributions. The repository has meaningful development commits. Publication remains pending approval; I will show the final repository link after it is actually published.
SOURCES:
reports/final_release_tests.json
tests/; README.md; Git commit history
Solo collaboration reflection: docs/programming_report.pdf

## Slide 11

TIME: 50 seconds
SAY:
A real failure showed that a mixed October weather and moderate-hike question could be reduced to hikes alone. The fix preserves the combined intent and still returns weather and visitation when trail records are unavailable. Another validation prevents a model from silently restricting an all-parks query. Trail coverage is deliberately limited to 17 reviewed routes across six park codes, with 57 inventory records lacking reviewed trails. Difficulty labels match official wording; missing details remain unknown. Point weather represents a location rather than a whole park. Park-wide recreation visits are only a proxy for crowding. SEKI combines two visitation records but uses one weather location. Live alerts are optional and require configuration. Cloud deployment, predictive forecasting, and itinerary generation are not claimed as completed features.
SOURCES:
docs/trail_issue_resolution.md; reports/trail_diagnostics.json; reports/trail_fix_live_verification.json; docs/methodology.md

## Slide 12

TIME: 180 seconds
SAY:
DEMO SCRIPT: First open the running local app. Clear activity filters if needed, show the discovery map, select Zion, and open the official guide and reviewed trail cards. Explain the source links. Second show visit rankings for 2005–2025, identify October, and change the weather versus crowds preference to demonstrate that a transparent score responds to user priorities. Open Data and methods briefly to show EDA and correlation cautions. Third open the Travel Assistant. Enter the key privately in the masked field if needed; never reveal it on the projector. Ask: I am visiting Zion National Park in October. Based on historical weather and crowds, would you recommend visiting then? What moderate hikes could I do, and why? Point to the historical evidence, Watchman source link, and actual provider-call evidence. Show that Badlands still provides seasonal statistics while clearly explaining its missing reviewed trail coverage. If the network is unavailable, show the labeled retained verification evidence and screenshots; do not claim a new successful call. Close: the project combines API acquisition, responsible EDA, modular Python, and a useful constrained LLM interface. Keep this demonstration to three minutes, leaving time for questions.
SOURCES:
https://www.nps.gov/arch/index.htm
https://www.nps.gov/common/uploads/structured_data/3C79931C-1DD8-B71B-0BF201E3DB540D04.jpg?maxWidth=1200&maxHeight=800&quality=90
https://www.nps.gov/aboutus/disclaimer.htm
docs/programming_demo.md
