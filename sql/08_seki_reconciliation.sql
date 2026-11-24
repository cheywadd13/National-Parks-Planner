-- Source components are bound JSON from the retained NPS CSV.
-- Exact component-key validation is performed by the runner before this query.
WITH components AS (
 SELECT * FROM jsonb_to_recordset(%(components_json)s::jsonb)
 AS x(park_code text,year int,month int,recreation_visits bigint)
), expected AS (
 SELECT year,month,sum(recreation_visits)::bigint AS expected_visits
 FROM components WHERE park_code IN ('SEQU','KICA')
   AND year BETWEEN %(start_year)s AND %(end_year)s
 GROUP BY year,month HAVING count(DISTINCT park_code)=2 AND count(recreation_visits)=2
), observed AS (
 SELECT year,month,recreation_visits AS observed_visits
 FROM public.visitation WHERE park_code='SEKI'
 AND year BETWEEN %(start_year)s AND %(end_year)s
)
SELECT coalesce(e.year,o.year) AS year,coalesce(e.month,o.month) AS month,
 e.expected_visits,o.observed_visits,o.observed_visits-e.expected_visits AS difference
FROM expected e FULL JOIN observed o USING (year,month)
ORDER BY year,month;
