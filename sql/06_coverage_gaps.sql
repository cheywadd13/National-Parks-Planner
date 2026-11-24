-- Explicit expected grid finds absent records that null checks cannot find.
WITH expected AS (
 SELECT p.park_code,y.year,m.month FROM public.parks p
 CROSS JOIN generate_series(%(start_year)s::int,%(end_year)s::int) y(year)
 CROSS JOIN generate_series(1,12) m(month)
)
SELECT e.*,v.park_code IS NULL AS missing_visitation,
       w.park_code IS NULL AS missing_weather
FROM expected e LEFT JOIN public.visitation v USING (park_code,year,month)
LEFT JOIN public.weather w USING (park_code,year,month)
WHERE v.park_code IS NULL OR w.park_code IS NULL
ORDER BY e.park_code,e.year,e.month;
