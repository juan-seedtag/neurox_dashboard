-- =============================================================================
-- Sofia — Consolidated Demand Base Query
-- =============================================================================
-- Single source of truth for all demand revenue analysis.
--
-- As of 2026-06-17 the heavy lifting (DSP mapping, channel unification, FX
-- conversion, and the O&O SSP / Beachfront / External UNIONs) is precomputed
-- UPSTREAM into a single curated table that refreshes DAILY:
--
--     st_datalakehouse.analytics.reporting_adex_demand
--
-- This file no longer rebuilds that logic inline. It simply exposes the curated
-- table through the `consolidated_demand` CTE, so every downstream consumer
-- (tools/build_sql.py, tools/weekly_forecast.py, tools/weekly_report.py) keeps
-- working unchanged — they read this file and append `FROM consolidated_demand`.
--
-- If the upstream table's schema ever changes, update the column list below and
-- it propagates everywhere automatically.
--
-- HOW TO USE
-- ----------
-- Append your own SELECT on top of the final `consolidated_demand` CTE:
--
--   <contents of this file>
--   SELECT
--       <your dimensions>,
--       SUM(revenue_gross) AS revenue_gross
--   FROM consolidated_demand
--   WHERE date BETWEEN DATE '...' AND DATE '...'
--   GROUP BY <your dimensions>
--
-- OUTPUT COLUMNS  (identical to the previous hand-built base)
-- --------------
--   date             DATE
--   connection_type  VARCHAR   Direct | Reseller | BidSwitch
--   business_line    VARCHAR   Open Auction - Seedtag | PMP Web - O&O | ...
--   publisher_country VARCHAR  ISO-2 code or region group (US, GB, MENA, ...)
--   product_category VARCHAR   Display | Native | Online Video | CTV | Other
--   dsp_group_name   VARCHAR   Normalised DSP name
--   clearvu_account  VARCHAR   ClearVu account (Beachfront Select only, else NULL)
--   channel_id       VARCHAR   Raw channel identifier
--   revenue_gross    DOUBLE    Gross revenue USD
-- =============================================================================

WITH consolidated_demand AS (
    SELECT
        date,
        connection_type,
        business_line,
        publisher_country,
        product_category,
        dsp_group_name,
        clearvu_account,
        channel_id,
        revenue_gross
    FROM st_datalakehouse.analytics.reporting_adex_demand
)
