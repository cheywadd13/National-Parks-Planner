-- Read-only metadata inspection. No trail schema or data is created.
SELECT table_name, table_type
FROM information_schema.tables
WHERE table_schema = 'public'
  AND (table_name ILIKE '%trail%' OR table_name ILIKE '%hik%');

SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (column_name ILIKE '%trail%' OR column_name ILIKE '%hike%');

-- Catalog park codes are checked against this inventory in the application audit.
SELECT park_code, park_name FROM public.parks ORDER BY park_code;

-- Exact fixed parameterized historical SELECT is in src/travel_queries.py.
-- Trail lookup currently reads data/trails.json, never a nonexistent SQL table.
