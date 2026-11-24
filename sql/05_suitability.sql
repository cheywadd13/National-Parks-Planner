-- SQL counterpart of src/recommendations.py.
-- Eligibility precedes crowd ranking. Missing months remain unscored.
WITH parameters AS (
 SELECT %(temp_low)s::float8 AS low,%(temp_high)s::float8 AS high,
        %(weather_weight)s::float8 AS ww,%(crowd_weight)s::float8 AS cw
), monthly AS (
 SELECT v.park_code,v.month,count(*) AS years,
  percentile_cont(.5) WITHIN GROUP (ORDER BY w.avg_temp_c) AS avg_temp_c,
  percentile_cont(.5) WITHIN GROUP (ORDER BY w.total_precip_mm) AS total_precip_mm,
  percentile_cont(.5) WITHIN GROUP (ORDER BY w.total_snowfall_cm) AS total_snowfall_cm,
  percentile_cont(.5) WITHIN GROUP (ORDER BY v.recreation_visits) AS recreation_visits
 FROM public.visitation v JOIN public.weather w USING (park_code,year,month)
 WHERE v.year BETWEEN %(start_year)s AND %(end_year)s AND v.recreation_visits >= 0
   AND w.avg_temp_c > '-Infinity'::float8 AND w.avg_temp_c < 'Infinity'::float8
   AND w.total_precip_mm >= 0 AND w.total_precip_mm < 'Infinity'::float8
   AND w.total_snowfall_cm >= 0 AND w.total_snowfall_cm < 'Infinity'::float8
 GROUP BY v.park_code,v.month
), eligible AS (
 SELECT *,count(*) OVER (PARTITION BY park_code) AS eligible_months,
  rank() OVER (PARTITION BY park_code ORDER BY recreation_visits) AS first_rank,
  count(*) OVER (PARTITION BY park_code,recreation_visits) AS tied_months
 FROM monthly WHERE years >= %(minimum_years)s
), components AS (
 SELECT e.*,
  100*greatest(0,1-(greatest(low-avg_temp_c,0)+greatest(avg_temp_c-high,0))/25) AS temperature_score,
  100*greatest(0,1-total_precip_mm/200) AS precipitation_score,
  100*greatest(0,1-total_snowfall_cm/60) AS snow_score,
  CASE WHEN eligible_months=1 THEN 50.0
       ELSE 100.0*(first_rank-1+(tied_months-1)/2.0)/(eligible_months-1) END AS crowd_percentile
 FROM eligible e CROSS JOIN parameters
), scored AS (
 SELECT *, .60*temperature_score+.25*precipitation_score+.15*snow_score AS weather_score,
         100-crowd_percentile AS crowd_score
 FROM components
), combined AS (
 SELECT s.*, (ww*weather_score+cw*crowd_score)/NULLIF(ww+cw,0) AS score
 FROM scored s CROSS JOIN parameters
 WHERE ww>=0 AND cw>=0 AND ww+cw>0 AND low<=high
), ranked AS (
 SELECT *,rank() OVER (PARTITION BY park_code ORDER BY score DESC) AS rank
 FROM combined
)
SELECT p.park_code,m.month,coalesce(a.years,0) AS years,
 a.avg_temp_c,a.total_precip_mm,a.total_snowfall_cm,a.recreation_visits,
 r.temperature_score,r.precipitation_score,r.snow_score,r.weather_score,
 r.crowd_percentile,r.crowd_score,r.score,r.rank
FROM public.parks p CROSS JOIN generate_series(1,12) AS m(month)
LEFT JOIN monthly a ON a.park_code=p.park_code AND a.month=m.month
LEFT JOIN ranked r ON r.park_code=p.park_code AND r.month=m.month
ORDER BY p.park_code,m.month;
