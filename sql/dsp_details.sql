-- =============================================================================
-- DSP Details — Section 2 (Internal)
-- =============================================================================
-- Deal / advertiser-level demand detail for a SINGLE DSP, unioned across the two
-- raw demand sources that carry deal_id + ad_name (reporting_adex_demand does not):
--
--   * Beachfront (BFM)  → st_datalakehouse.analytics.bfm_demand
--   * Seedtag O&O SSP   → st_datalakehouse.analytics.etl_ssp_responses_daily_enriched
--
-- Aggregated to MONTHLY grain (period) per deal/advertiser so the report can pivot
-- months into columns while a single-DSP pull stays small.
--
-- Each row is classified into deal_type (drives the PMP / Curation / Open Auction views)
-- by an EXACT, hard-coded match on business_line — Beachfront uses its native
-- business_line; the SSP source has no business_line column, so one is constructed
-- from product_type (see the `seedtag` CTE). Mapping:
--   'Open Auction' → 'Open Auction - BFM', 'Open Auction - Seedtag'
--   'Curation'     → 'Select - BFM', 'PMP - Curation'
--   'PMP'          → 'DSP Marketplace - BFM', 'PMP - Seedtag', 'PMP Web - O&O', 'PMP CTV - O&O'
-- Anything else (e.g. 'Direct Web - O&O', 'None') gets deal_type = NULL and is dropped.
--
-- Coverage: EVERY deal is represented. Deals are ranked by total revenue within
-- (DSP, deal_type); individual rows are kept while cumulative revenue is within
-- {coverage} of the deal_type total (always at least {min_deals} deals, never more
-- than {max_deals}). The remainder is rolled up into ONE "long tail" row per month
-- (is_tail = TRUE, tail_deals = how many deals it aggregates), so per-deal_type
-- totals reconcile exactly — nothing is dropped.
--
-- Placeholders (filled by tools/query_builders.dsp_details_query):
--   {date_from} {date_to}   ISO date strings
--   {bfm_dsp_and}           optional "AND COALESCE(m.dsp_label, a.advertiser) = '<dsp>'"
--   {ssp_dsp_and}           optional "AND s.dsp_group_name = '<dsp>'"
--   {min_deals}             deals always kept individually per deal_type
--   {coverage}              cumulative revenue share kept individually (e.g. 0.995)
--   {max_deals}             hard cap on individually-kept deals per deal_type
-- =============================================================================

WITH beachfront AS (
    SELECT
        CAST(DATE_TRUNC('month', a.date) AS date)    AS period,
        dsp_group_name                               AS dsp_group_name,
        'Beachfront'                                 AS source,
        a.business_line                              AS business_line,
        a.clearvu_account                            AS clearvu_account,
        a.deal_name                                  AS ad_name,
        a.deal_id                                    AS deal_id,
        a.adomain                                    AS adomain,
        channel_id                                   AS channel_id,
        SUM(a.revenue)                               AS revenue_gross
    FROM st_datalakehouse.analytics.reporting_closing_bfm_demand a
    WHERE a.date >= DATE '{date_from}' AND a.date <= DATE '{date_to}'
      AND (a.clearvu_account IS NULL)
      {bfm_dsp_and}
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
),

seedtag AS (
    SELECT
        CAST(DATE_TRUNC('month', s.date) AS date)    AS period,
        s.dsp_group_name                             AS dsp_group_name,
        'Seedtag SSP'                                AS source,
        -- SSP has no business_line column; construct it from product_type so it
        -- matches the reporting_adex_demand vocabulary the deal_type CASE keys off.
        CASE WHEN s.product_type LIKE 'O%'        THEN 'Open Auction - Seedtag'
             WHEN s.product_type LIKE 'P%'        THEN 'PMP Web - O&O'
             WHEN s.product_type LIKE 'D%'        THEN 'Direct Web - O&O'
             WHEN s.product_type LIKE 'Curation%' THEN 'PMP - Curation'
        END                                          AS business_line,
        CAST(NULL AS varchar)                        AS clearvu_account,
        s.deal_name                                  AS ad_name,
        s.deal_id                                    AS deal_id,
        COALESCE(s.buyer_name, s.adomain)            AS advertiser,
        s.channel_id                                 AS channel_id,
        SUM(CAST(s.seedtag_revenue AS double))       AS revenue_gross
    FROM st_datalakehouse.analytics.etl_ssp_responses_daily_enriched s
    WHERE s.date >= DATE '{date_from}' AND s.date <= DATE '{date_to}' and channel_id <> 'Beachfront'
      {ssp_dsp_and}
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8, 9
),

-- Hard-coded deal_type from business_line (see header). Rows whose business_line
-- maps to no bucket (e.g. 'Direct Web - O&O', 'None', NULL) get deal_type = NULL
-- and are dropped here, so only PMP / Curation / Open Auction reach the report.
base AS (
    SELECT * FROM (
        SELECT u.*,
            CASE
                WHEN business_line IN ('Open Auction - BFM', 'Open Auction - Seedtag') THEN 'Open Auction'
                WHEN business_line IN ('Select - BFM', 'PMP - Curation')                THEN 'Curation'
                WHEN business_line IN ('DSP Marketplace - BFM', 'PMP - Seedtag',
                                       'PMP Web - O&O', 'PMP CTV - O&O')                THEN 'PMP'
            END AS deal_type
        FROM (SELECT * FROM beachfront UNION ALL SELECT * FROM seedtag) u
        WHERE revenue_gross > 0
    )
    WHERE deal_type IS NOT NULL
),

-- Attach per-deal total (across months) and the per-deal_type grand total.
-- Deal identity is (ad_name, deal_id) for PMP/Curation — the same deal seen through
-- several channels/sources counts ONCE. Open Auction has no deals, so its identity
-- is the advertiser (+ channel).
enriched AS (
    SELECT
        base.*,
        CASE WHEN deal_type = 'Open Auction' THEN advertiser END AS oa_advertiser,
        CASE WHEN deal_type = 'Open Auction' THEN channel_id END AS oa_channel_id,
        SUM(revenue_gross) OVER (
            PARTITION BY dsp_group_name, deal_type,
                         ad_name, deal_id,
                         CASE WHEN deal_type = 'Open Auction' THEN advertiser END,
                         CASE WHEN deal_type = 'Open Auction' THEN channel_id END
        ) AS deal_total,
        SUM(revenue_gross) OVER (PARTITION BY dsp_group_name, deal_type) AS deal_type_total_revenue
    FROM base
),

-- Rank DEALS (not month-rows) within each (DSP, deal_type) by total revenue,
-- tie-broken by ad_name then deal_id. Ranking per-DSP means dsp=None covers
-- every DSP in one scan.
ranked AS (
    SELECT
        enriched.*,
        DENSE_RANK() OVER (
            PARTITION BY dsp_group_name, deal_type
            ORDER BY deal_total DESC,
                     ad_name, deal_id, oa_advertiser, oa_channel_id
        ) AS deal_rn
    FROM enriched
),

ranked2 AS (
    SELECT ranked.*, MAX(deal_rn) OVER (PARTITION BY dsp_group_name, deal_type) AS deal_type_total_rows
    FROM ranked
),

-- Cumulative revenue by deal rank (count each deal's total once, on its first month-row).
marked AS (
    SELECT ranked2.*,
           ROW_NUMBER() OVER (PARTITION BY dsp_group_name, deal_type, deal_rn ORDER BY period) AS month_rn
    FROM ranked2
),
cum AS (
    SELECT marked.*,
           SUM(CASE WHEN month_rn = 1 THEN deal_total ELSE 0 END) OVER (
               PARTITION BY dsp_group_name, deal_type ORDER BY deal_rn
           ) AS cum_revenue
    FROM marked
),

-- keep = shown as its own row; the rest feeds the long-tail rollup.
flagged AS (
    SELECT cum.*,
           (deal_rn <= {min_deals}
            OR (deal_rn <= {max_deals}
                AND cum_revenue <= {coverage} * deal_type_total_revenue)) AS keep
    FROM cum
),
flagged2 AS (
    SELECT flagged.*,
           MAX(CASE WHEN keep THEN deal_rn ELSE 0 END) OVER (
               PARTITION BY dsp_group_name, deal_type
           ) AS kept_deals
    FROM flagged
)

SELECT
    period,
    dsp_group_name,
    source,
    business_line,
    deal_type,
    clearvu_account,
    ad_name,
    deal_id,
    advertiser,
    channel_id,
    revenue_gross,
    deal_total,
    deal_type_total_revenue,
    deal_type_total_rows,
    FALSE               AS is_tail,
    CAST(NULL AS bigint) AS tail_deals
FROM flagged2
WHERE keep

UNION ALL

-- One rollup row per month for everything below the coverage cutoff.
SELECT
    period,
    dsp_group_name,
    'Mixed'              AS source,
    CAST(NULL AS varchar) AS business_line,
    deal_type,
    CAST(NULL AS varchar) AS clearvu_account,
    CAST(NULL AS varchar) AS ad_name,
    CAST(NULL AS varchar) AS deal_id,
    CAST(NULL AS varchar) AS advertiser,
    CAST(NULL AS varchar) AS channel_id,
    SUM(revenue_gross)   AS revenue_gross,
    SUM(SUM(revenue_gross)) OVER (PARTITION BY dsp_group_name, deal_type) AS deal_total,
    MAX(deal_type_total_revenue) AS deal_type_total_revenue,
    MAX(deal_type_total_rows)    AS deal_type_total_rows,
    TRUE                 AS is_tail,
    MAX(deal_type_total_rows) - MAX(kept_deals) AS tail_deals
FROM flagged2
WHERE NOT keep
GROUP BY period, dsp_group_name, deal_type

ORDER BY deal_type, is_tail, deal_total DESC, period
