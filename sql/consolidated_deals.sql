-- =============================================================================
-- Consolidated Deals — feeds BOTH dashboard tabs
-- =============================================================================
-- Consolidation of deal-based demand (Open Auction excluded — the Open Auction
-- tab is fed by the separate, lighter sql/open_auction.sql):
--   * Beachfront (reporting_closing_bfm_demand — curated CLOSING table with
--     Finance-adjusted revenue and pre-normalised DSP/channel/deal fields),
--     business_line <> 'Open Auction - BFM'.
--   * Seedtag O&O SSP (stg_ssp_responses_daily), PMP only (product_type 'P%'),
--     bidder_dsp_mapping + channel-based DSP resolution.
-- Active deal on BOTH branches = had bid responses in the period.
--
-- Returned at DEAL grain per quarter; the report aggregates client-side:
--   Tab 1 (DSP Overview):  advertiser × quarter → distinct-deal count, revenue,
--                          avg spend per deal, QoQ / YoY variations
--   Tab 2 (Deal Overview): clearvu_account, ad_name, deal_id × quarter → rev_gross,
--                          plus current-quarter QTD / QoQ % / YoY %
--
-- Day-matched comparison windows: the current quarter has only N completed days
-- (N = days elapsed before {build_date}), so its QoQ/YoY comparisons must use the
-- SAME N days of the previous quarter / prior-year quarter. Three conditional sums
-- (rev_qtd_*) are computed in the same scan; each lands on the deal's row for the
-- window's own quarter, and the client sums them per DSP/deal. Completed quarters
-- compare full data client-side from rev_gross — no extra queries.
--
-- Placeholders: {date_from} / {date_to} (ISO dates, [from, to) on both sources),
-- {build_date} (ISO date). The build runs this query ONCE PER QUARTER chunk and
-- concatenates — one statement over the full range exceeds cluster memory.
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
),

-- IMPORTANT (memory): both branches aggregate DIRECTLY to quarter grain, with the
-- day-matched window sums computed inline from the raw dates (CASE runs before the
-- aggregation). A day-grain intermediate (quarter added later) blows the cluster
-- memory limit on the SSP branch — never reintroduce it.
--
-- Beachfront comes from reporting_closing_bfm_demand — the curated CLOSING table
-- (Finance-adjusted revenue; dsp_group_name / channel_id / deal_name /
-- product_category already normalised upstream, so no seat/mapping joins here).
-- Active deal = had bid responses in the period (HAVING).
bfx AS (
    SELECT
        CAST(date_trunc('quarter', b.date) AS date) AS quarter
        , b.dsp_group_name AS advertiser
        , b.channel_id
        , b.clearvu_account
        , b.deal_id
        , b.business_line
        , b.deal_name AS ad_name
        , b.product_category
        , SUM(b.revenue) AS rev_gross
        , SUM(b.revenue_net) AS rev_net
        , SUM(b.total_response_bids) AS outgoing_bids
        , SUM(b.total_impressions) AS impressions
        , SUM(CASE WHEN b.date >= w.curr_q_start   AND b.date < w.curr_q_end   THEN b.revenue END) AS rev_qtd_current
        , SUM(CASE WHEN b.date >= w.prev_q_q_start AND b.date < w.prev_q_q_end THEN b.revenue END) AS rev_qtd_prev_qtd
        , SUM(CASE WHEN b.date >= w.prev_y_q_start AND b.date < w.prev_y_q_end THEN b.revenue END) AS rev_qtd_prev_year
    FROM st_datalakehouse.analytics.reporting_closing_bfm_demand b
    CROSS JOIN windows w
    WHERE 1=1
      AND b.date >= DATE '{date_from}' AND b.date < DATE '{date_to}'
      -- Open Auction lives in its own light query (sql/open_auction.sql)
      AND b.business_line <> 'Open Auction - BFM'
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    HAVING SUM(b.total_response_bids) > 0
),

stx AS (
    SELECT
        CAST(date_trunc('quarter', r.date) AS date) AS quarter
        , COALESCE(
            CASE
                WHEN r.channel_id IN ('Nexxen','TheTradeDesk','Opera','Sportradar','RtbHouse','Beeswax','MediaForce','Stackadapt','Illumin') THEN r.channel_id
                WHEN r.channel_id IN ('LoopMe','Adform','OneTag','AdYouLike') THEN 'DSP Not Found'
                WHEN r.channel_id IN ('DBM','GDN') THEN 'DV360'
                WHEN r.channel_id = 'Outbrain' THEN 'Outbrain/Teads'
                WHEN r.channel_id = 'StackAdaptDSP' THEN 'StackAdapt'
                WHEN (r.channel_id IN ('Outbrain','DBM','Nexxen','TheTradeDesk','Opera','Sportradar','RtbHouse','Beeswax','MediaForce','GDN','StackAdapt','Illumin','NextRoll','StackAdaptDSP','AdMixerBidswitch','Viant')) AND (b.dsp_group_name IS NULL) THEN r.channel_id
                ELSE b.dsp_group_name
            END, b.dsp_name
          ) AS advertiser
        , r.channel_id
        , NULL AS clearvu_account
        , deal_id
        , 'PMP Web - O&O' AS business_line
        , deal_name AS ad_name
        , CASE
            WHEN r.product_category = 'Video' THEN 'Online Video'
            ELSE r.product_category
          END AS product_category
        , SUM(r.net_imp_paid) / 1000.0 AS rev_gross
        , 0 AS rev_net
        , SUM(total_response_bids) AS outgoing_bids
        , SUM(total_impressions) AS impressions
        , SUM(CASE WHEN r.date >= w.curr_q_start   AND r.date < w.curr_q_end   THEN r.net_imp_paid END) / 1000.0 AS rev_qtd_current
        , SUM(CASE WHEN r.date >= w.prev_q_q_start AND r.date < w.prev_q_q_end THEN r.net_imp_paid END) / 1000.0 AS rev_qtd_prev_qtd
        , SUM(CASE WHEN r.date >= w.prev_y_q_start AND r.date < w.prev_y_q_end THEN r.net_imp_paid END) / 1000.0 AS rev_qtd_prev_year
    FROM st_datalakehouse.analytics.stg_ssp_responses_daily r
    LEFT JOIN st_datalakehouse.analytics.bidder_dsp_mapping b
        ON r.bidder_id = b.bidder_id AND r.channel_id = b.channel_name
    CROSS JOIN windows w
    WHERE 1=1
      AND r.date >= DATE '{date_from}' AND r.date < DATE '{date_to}'
      AND r.channel_id <> 'Beachfront'
      AND product_type LIKE 'P%'
      AND r.source_type NOT IN ('Beachfront', 'SpringServe')
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
    HAVING SUM(total_response_bids) > 0
),

consolidated AS (
    SELECT quarter, deal_id, advertiser, channel_id, clearvu_account,
           business_line, ad_name, product_category,
           rev_gross, impressions, outgoing_bids, rev_qtd_current, rev_qtd_prev_qtd, rev_qtd_prev_year
    FROM bfx
    UNION ALL
    SELECT quarter, deal_id, advertiser, channel_id, clearvu_account,
           business_line, ad_name, product_category,
           rev_gross, impressions, outgoing_bids, rev_qtd_current, rev_qtd_prev_qtd, rev_qtd_prev_year
    FROM stx
)

-- Merge the two quarter-grain branches down to the report grain. Window sums were
-- computed inline in each branch; each lands on the row of its own quarter.
SELECT
    quarter
    , advertiser
    , business_line
    , channel_id
    , clearvu_account
    , ad_name
    , deal_id
    , SUM(rev_gross) AS rev_gross
    , SUM(impressions) AS impressions
    , SUM(outgoing_bids) AS outgoing_bids
    , SUM(rev_qtd_current)   AS rev_qtd_current
    , SUM(rev_qtd_prev_qtd)  AS rev_qtd_prev_qtd
    , SUM(rev_qtd_prev_year) AS rev_qtd_prev_year
FROM consolidated
GROUP BY 1, 2, 3, 4, 5, 6, 7
ORDER BY rev_gross DESC
