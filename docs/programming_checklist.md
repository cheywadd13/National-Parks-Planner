# Programming submission checklist

The official rubric assigns 20% to each category. Implementation is not a grade.

| Requirement | Evidence | Status |
| --- | --- | --- |
| External API acquisition, structure and storage | `src/etl/extract.py`, `verify_weather.py`, raw JSON and lineage | Implemented; representative acquisition evidence retained |
| Descriptive statistics and charts | Data & methods; `src/analytics.py`, Plotly | Implemented |
| Missing values and outlier treatment | `src/eda.py`; seasonal IQR diagnostics, retained source values, sensitivity means | Implemented and tested |
| Correlation and interpretation | Raw/month-adjusted Spearman, sample counts and on-screen noncausal explanation | Implemented |
| Findings in Streamlit | Computed peak/quiet month summaries | Implemented |
| Meaningful LLM API integration | `src/assistant.py`, `assistant_ui.py`, fixed query functions; `reports/openai_verification.json` | Five real GPT-6 Luna Standard calls observed; corrected combined question verified by provider receipt and user confirmation |
| Direct in-app LLM UI and follow-ups | Travel assistant, session preferences and evidence panel | Implemented; actual model interpretation needs live demonstration |
| Modular code, guidance and failures | Separate data, EDA, content, API, assistant and visualization modules | Implemented; tests cover missing keys, failures and invalid outputs |
| Git/GitHub meaningful history | Local release repository and phase commits | Verify final local history; remote publication remains pending until available |
| README setup, sources and run instructions | `README.md`, requirements, secrets example | Updated |
| Separate 2–3 page report with screenshots | `docs/programming_report.pdf` | Updated with real API verification and remaining coverage limits |
| Solo collaboration/lessons reflection | Report identifies solo authorship and AI assistance | Included; student should personalize reflection |
| Local/hosted working application | Streamlit preview and startup instructions | Local release available; hosted deployment optional |
| Live demo ≤15 minutes | `docs/programming_demo.md` | Script ready; student rehearsal and actual presentation pending |
| GitHub/report portal submission | Student account `cheywadd13` | Student action pending; do not mistake a profile URL for a repository |

Current evidence must be read with `reports/programming_tests.json` and
`reports/programming_live_verification.json`; mocked tests are never labeled
as successful live LLM requests. Existing database reports and SQL are preserved.

## Final release evidence

The complete final run passed all 38 tests with no failures, errors or skips, including live read-only checks. See `reports/final_release_tests.json` and `docs/release_readiness.md`. The 12-slide Programming deck with detailed notes is in `presentations/National_Parks_Programming_Final.pptx`. GitHub publication awaits owner approval.
