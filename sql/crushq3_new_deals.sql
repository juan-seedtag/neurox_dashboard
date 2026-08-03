-- New deal activations tracker (Tracker tab of beachfront_adname_loss_dashboard)
-- A deal counts as "new" on the first date it ever appears in
-- reporting_closing_bfm_demand (history starts 2025-01-01).
-- Single pass over the table; the UI filters by activation month client-side
-- (Jul 2026 / Aug 2026 / Global), so pull everything activated since 2026-07-01
-- when refreshing.

WITH deal_first AS (
  SELECT
    deal_name,
    MIN(date)                                     AS activation_date,
    MAX_BY(dsp_group_name, date)                  AS dsp_group_name,
    MAX_BY(clearvu_account, date)                 AS clearvu_account,
    MAX_BY(business_line, date)                   AS business_line,
    ARRAY_JOIN(ARRAY_AGG(DISTINCT deal_id), ', ') AS deal_ids,
    SUM(revenue)                                  AS revenue_since_activation,
    COUNT(DISTINCT date)                          AS active_days,
    MAX(date)                                     AS last_seen
  FROM st_datalakehouse.analytics.reporting_closing_bfm_demand
  GROUP BY 1
)
SELECT *
FROM deal_first
WHERE activation_date >= DATE '2026-07-01'
  AND business_line not in ('PMP - Seedtag', 'Open Auction - BFM')
ORDER BY activation_date, revenue_since_activation DESC
