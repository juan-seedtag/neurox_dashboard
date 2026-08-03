-- =============================================================================
-- Open Auction — feeds the Open Auction tab (ad_name × quarter)
-- =============================================================================
-- Beachfront 'Open Auction - BFM' only (SSP OMP has no ad_name), from
-- reporting_closing_bfm_demand — the curated CLOSING table (Finance-adjusted
-- revenue; dsp_group_name / deal_name pre-normalised, so no seat/mapping joins).
-- Kept as a SEPARATE query from consolidated_deals.sql so the heavy SSP scan and
-- this one never share a statement (cluster memory).
--
-- Same day-matched windows as the deals query: the current quarter's QoQ/YoY use
-- the first N completed days vs the same N days of the comparison quarters.
--
-- Placeholders: {date_from} (ISO date), {build_date} (ISO date).
-- =============================================================================

WITH params AS (
    SELECT
        date_trunc('quarter', DATE '{build_date}')                                 AS curr_q_start,
        date_trunc('quarter', DATE '{build_date}') - INTERVAL '1' YEAR             AS prev_y_q_start,
        date_trunc('quarter', DATE '{build_date}') - INTERVAL '3' MONTH            AS prev_q_q_start,
        date_diff('day', date_trunc('quarter', DATE '{build_date}'), DATE '{build_date}') AS days
),

windows AS (
    SELECT
        curr_q_start,
        date_add('day', days, curr_q_start)   AS curr_q_end,     -- exclusive
        prev_q_q_start,
        date_add('day', days, prev_q_q_start) AS prev_q_q_end,   -- exclusive
        prev_y_q_start,
        date_add('day', days, prev_y_q_start) AS prev_y_q_end    -- exclusive
    FROM params
)

SELECT
    CAST(date_trunc('quarter', o.date) AS date) AS quarter
    , o.dsp_group_name AS advertiser
    , o.deal_name AS ad_name
    , SUM(o.revenue) AS rev_gross
    , SUM(CASE WHEN o.date >= w.curr_q_start   AND o.date < w.curr_q_end   THEN o.revenue END) AS rev_qtd_current
    , SUM(CASE WHEN o.date >= w.prev_q_q_start AND o.date < w.prev_q_q_end THEN o.revenue END) AS rev_qtd_prev_qtd
    , SUM(CASE WHEN o.date >= w.prev_y_q_start AND o.date < w.prev_y_q_end THEN o.revenue END) AS rev_qtd_prev_year
FROM st_datalakehouse.analytics.reporting_closing_bfm_demand o
CROSS JOIN windows w
WHERE o.date >= DATE '{date_from}'
  AND o.business_line = 'Open Auction - BFM'
GROUP BY 1, 2, 3
HAVING SUM(o.revenue) > 0
ORDER BY rev_gross DESC
