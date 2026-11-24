-- Within-park seasonal medians and tie-preserving ranks.
WITH monthly AS (
 SELECT park_code,month,count(*) AS years,
        percentile_cont(0.5) WITHIN GROUP (ORDER BY recreation_visits) AS median_visits
 FROM public.visitation
 WHERE year BETWEEN %(start_year)s AND %(end_year)s AND recreation_visits >= 0
 GROUP BY park_code,month
 HAVING count(*) >= %(minimum_years)s
), ranked AS (
 SELECT *,rank() OVER (PARTITION BY park_code ORDER BY median_visits) AS quiet_rank,
        max(median_visits) OVER (PARTITION BY park_code) AS peak_month_visits
 FROM monthly
)
SELECT p.park_name,r.*,
       100.0*median_visits/NULLIF(peak_month_visits,0) AS pct_of_park_peak
FROM ranked r JOIN public.parks p USING (park_code)
WHERE quiet_rank <= %(top_n)s
ORDER BY park_code,quiet_rank,month;
