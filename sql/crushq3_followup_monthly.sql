-- Follow-up months for the loss tabs (DSP Marketplace / Select / Open Auction)
-- of beachfront_adname_loss_dashboard. Pulls:
--   * every closed month after the Jun 2026 baseline (>= 2026-07-01)
--   * H2-2025 months, used as prior-year bases for the YoY row
-- The dashboard build aggregates this client-side to each table granularity
-- (dsp / cva / ad and combinations) and appends the columns after a separator.

SELECT
  CAST(date_trunc('month', date) AS varchar)              AS m,
  business_line                                           AS bl,
  COALESCE(NULLIF(dsp_group_name, ''), '—')               AS dsp,
  COALESCE(NULLIF(NULLIF(clearvu_account, ''), 'nan'), '—') AS cva,
  deal_name                                               AS ad,
  ARRAY_JOIN(ARRAY_AGG(DISTINCT regexp_replace(CAST(deal_id AS varchar), '\.0$', '')) FILTER (WHERE deal_id IS NOT NULL AND CAST(deal_id AS varchar) NOT IN ('nan','')), ', ') AS did,
  ROUND(SUM(revenue), 2)                                  AS rev
FROM st_datalakehouse.analytics.reporting_closing_bfm_demand
WHERE (date BETWEEN DATE '2025-07-01' AND DATE '2025-12-31'
       OR date >= DATE '2026-07-01')
  AND business_line <> 'PMP - Seedtag'
GROUP BY 1, 2, 3, 4, 5
