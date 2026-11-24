-- Means of monthly observations, with explicit independent support counts.
SELECT park_code,month,
 count(avg_temp_c) AS temperature_years,
 count(total_precip_mm) AS precipitation_years,
 count(total_snowfall_cm) AS snowfall_years,
 avg(avg_temp_c) AS avg_temp_c,
 avg(total_precip_mm) AS total_precip_mm,
 avg(total_snowfall_cm) AS total_snowfall_cm,
 stddev_samp(avg_temp_c) AS temperature_sd_c
FROM public.weather
WHERE year BETWEEN %(start_year)s AND %(end_year)s
GROUP BY park_code,month ORDER BY park_code,month;
