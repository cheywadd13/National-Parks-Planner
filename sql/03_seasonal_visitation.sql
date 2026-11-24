-- Calendar-year seasons. Winter is Jan + Feb + Dec of the SAME year.
-- Compare totals only for complete twelve-month park-years.
WITH complete AS (
 SELECT park_code,year,sum(recreation_visits)::bigint AS annual_visits
 FROM public.visitation
 WHERE year BETWEEN %(start_year)s AND %(end_year)s AND recreation_visits >= 0
 GROUP BY park_code,year HAVING count(*) = 12
), seasons AS (
 SELECT v.park_code,v.year,
        CASE WHEN month IN (12,1,2) THEN 'Winter'
             WHEN month IN (3,4,5) THEN 'Spring'
             WHEN month IN (6,7,8) THEN 'Summer' ELSE 'Autumn' END AS season,
        sum(v.recreation_visits)::bigint AS season_visits,c.annual_visits
 FROM public.visitation v JOIN complete c USING (park_code,year)
 GROUP BY v.park_code,v.year,season,c.annual_visits
)
SELECT *,100.0*season_visits/NULLIF(annual_visits,0) AS pct_of_annual_visits
FROM seasons ORDER BY park_code,year,season;
