# Programming live demo — solo project

Target: 12 minutes, with a 3-minute buffer; never exceed the rubric's 15 minutes.
Submission target is Monday, November 23, 2026, as supplied by the student.
No final video is included or required by this preparation.

| Time | Action | Point to explain |
| --- | --- | --- |
| 0:00–1:00 | Introduce the travel question and show Explore map | One app connects where, what and when; 63 reporting records, not an automatic claim of 63 distinct designated parks |
| 1:00–2:30 | Explain Open-Meteo acquisition; show stored raw JSON and source manifest | API → immutable source → unit-aware monthly transformation; distinguish retained evidence from a fresh request |
| 2:30–4:30 | Select Acadia; open activities and Hikes & trail details | Official links/photography; route lengths and unknown fields stay faithful to source; partial catalog |
| 4:30–7:00 | Open Data & methods; choose Yellowstone; change years | Descriptive statistics, missingness, seasonal IQR flags, retained extremes and sensitivity; raw versus month-adjusted Spearman, no causality claim |
| 7:00–9:00 | Open Travel assistant; ask October quiet-parks question; follow up “And March?” | Show live API interpretation and retrieved evidence; distinguish absolute visits from within-park crowd percentiles |
| 9:00–10:00 | Ask “Compare September and July in Yellowstone” | Component arithmetic explains the actual winning month; no assumed conclusion |
| 10:00–11:00 | Show comparison or modify weather/crowd preference | Personalization uses historical evidence and transparent weights |
| 11:00–12:00 | Show repository/tests and state limitations | Solo work, honest AI assistance, secure keys, incomplete trails, current alerts need NPS key, no forecasting |

## Before class

- Configure real `DATABASE_URL`, `OPENAI_API_KEY`, and optional `NPS_API_KEY` in
  the server environment or ignored Streamlit secrets. Never show the secrets file.
- Restart app, confirm live Supabase source indicator, and verify a successful
  LLM answer. Expand its evidence panel; record actual provider usage without keys.
- Try the follow-up and compare-month examples. Interpretation failures should
  be clarified, not hidden with canned results. A mocked test is not a live call.
- Keep the final report, actual repository URL and README open. Verify the report
  is 2–3 pages and the uploaded repository includes screenshots and the PDF.
- Run tests and keep the dated results. Verify the app locally from the README.
- Rehearse under 12 minutes. Check projection readability and internet access.

## Recovery

If an external API fails, show the honest unavailable message, then demonstrate
the verified non-LLM views and explain caching/fallback. A screenshot of a prior
real API result may be shown only as labeled prior evidence. A missing key means
LLM integration has not yet been demonstrated live; do not claim otherwise.
If Supabase fails, local CSV mode is explicitly labeled incomplete and is not
evidence of a live database query. No retry should write to the database.

## Final submission checklist

- Real GitHub repository URL under the student's account, with meaningful commits.
- Programming report PDF (2–3 pages) in repository and submission portal.
- Hosted app URL if hosted; otherwise reproducible local application instructions.
- Actual live LLM verification and demo rehearsal complete.
- Both course reports remain separate; no fabricated teammate contributions.
