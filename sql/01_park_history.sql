-- One row per observed park-month. Full key prevents many-to-many multiplication.
SELECT p.park_code,p.park_name,p.state,v.year,v.month,v.recreation_visits,
       w.avg_temp_c,w.total_precip_mm,w.total_snowfall_cm
FROM public.parks p
JOIN public.visitation v USING (park_code)
LEFT JOIN public.weather w USING (park_code,year,month)
WHERE p.park_code = %(park_code)s AND v.year BETWEEN %(start_year)s AND %(end_year)s
ORDER BY v.year,v.month;
