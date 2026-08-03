-- Daily revenue per new deal (Tracker tab line charts).
-- One row per (day, deal_name) for deals first activated on/after 2026-07-01;
-- the dashboard fills missing days with $0 client-side.

WITH deal_first AS (
  SELECT deal_name, MIN(date) AS activation_date
  FROM st_datalakehouse.analytics.reporting_closing_bfm_demand
  GROUP BY 1
)
SELECT
  CAST(t.date AS varchar)  AS d,
  t.deal_name              AS ad,
  ROUND(SUM(t.revenue), 2) AS rev
FROM st_datalakehouse.analytics.reporting_closing_bfm_demand t
JOIN deal_first f ON f.deal_name = t.deal_name
WHERE f.activation_date >= DATE '2026-07-01'
GROUP BY 1, 2
