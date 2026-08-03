-- Exact monthly revenue for the Jan 2025 – Jun 2026 baseline of the loss tabs.
-- Embedded into the dashboard so CSV exports carry exact values (the table
-- cells themselves render rounded, e.g. "20.0k"). Aggregated client-side to
-- each table granularity for the keys displayed in the HTML.

SELECT
  CAST(date_trunc('month', date) AS varchar)                AS m,
  business_line                                             AS bl,
  COALESCE(NULLIF(dsp_group_name, ''), '—')                 AS dsp,
  COALESCE(NULLIF(NULLIF(clearvu_account, ''), 'nan'), '—') AS cva,
  deal_name                                                 AS ad,
  ARRAY_JOIN(ARRAY_AGG(DISTINCT regexp_replace(CAST(deal_id AS varchar), '\.0$', '')) FILTER (WHERE deal_id IS NOT NULL AND CAST(deal_id AS varchar) NOT IN ('nan','')), ', ') AS did,
  ROUND(SUM(revenue), 2)                                    AS rev
FROM st_datalakehouse.analytics.reporting_closing_bfm_demand
WHERE date BETWEEN DATE '2025-01-01' AND DATE '2026-06-30'
  AND business_line <> 'PMP - Seedtag'
GROUP BY 1, 2, 3, 4, 5
