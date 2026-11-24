-- LAG compares only adjacent complete calendar years.
WITH annual AS (
 SELECT park_code,year,sum(recreation_visits)::bigint AS annual_visits
 FROM public.visitation WHERE year BETWEEN %(start_year)s AND %(end_year)s
   AND recreation_visits >= 0
 GROUP BY park_code,year HAVING count(*)=12
), previous AS (
 SELECT *,lag(year) OVER series AS previous_year,
          lag(annual_visits) OVER series AS previous_visits
 FROM annual WINDOW series AS (PARTITION BY park_code ORDER BY year)
)
SELECT *,CASE WHEN year=previous_year+1
              THEN 100.0*(annual_visits-previous_visits)/NULLIF(previous_visits,0)
         END AS year_over_year_pct
FROM previous ORDER BY park_code,year;
