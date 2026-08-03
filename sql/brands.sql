-- =============================================================================
-- Brand Details — feeds Tab 3 (which brands invest where)
-- =============================================================================
-- Brand (adomain) × DSP group × quarter, consolidated from:
--   * Seedtag O&O SSP (stg_ssp_responses_daily) with channel-based DSP
--     resolution + bidder_dsp_mapping fallback, adomain from bid responses.
--   * Beachfront (reporting_closing_bfm_demand — curated CLOSING table with
--     adomain and normalised DSP/channel fields).
-- NeuroX scope on both branches: connection_type <> 'Reseller' and Direct
-- business lines excluded. Brand = first label of the adomain.
--
-- Data starts 2025-06-01 (adomain not reliably populated before). Like the
-- deals query, the build runs this ONE QUARTER AT A TIME ({date_from} /
-- {date_to}, [from, to)) and concatenates — cluster memory.
-- HAVING thresholds trim the long tail so the embedded dataset stays small,
-- and a final cumulative-share filter keeps, within each
-- quarter × dsp_group × channel × business_line × connection_type group, only
-- the top brands that together make up 90% of the group's revenue — the
-- brand that crosses the 90% line is included, everything after is discarded.
-- =============================================================================

WITH consolidated_raw AS (
    SELECT
        CAST(date_trunc('quarter', r.date) AS date) AS quarter
        , COALESCE(
            CASE
                WHEN r.channel_id IN ('Nexxen','TheTradeDesk','Opera','Sportradar','RtbHouse','Beeswax','MediaForce','StackAdapt','Illumin') THEN r.channel_id
                WHEN r.channel_id IN ('LoopMe','Adform','OneTag','AdYouLike') THEN 'DSP Not Found'
                WHEN r.channel_id IN ('DBM','GDN') THEN 'DV360'
                WHEN r.channel_id = 'Outbrain' THEN 'Outbrain/Teads'
                WHEN r.channel_id = 'StackAdaptDSP' THEN 'StackAdapt'
                WHEN (r.channel_id IN ('Outbrain','DBM','Nexxen','TheTradeDesk','Opera','Sportradar','RtbHouse','Beeswax','MediaForce','GDN','StackAdapt','Illumin','NextRoll','StackAdaptDSP','AdMixerBidswitch','Viant')) AND (b.dsp_group_name IS NULL) THEN r.channel_id
                ELSE b.dsp_group_name
            END, b.dsp_name
          ) AS dsp_group_name
        , r.channel_id
        , split_part(r.adomain, '.', 1) AS adomain
        , CASE
            WHEN product_type LIKE 'O%' THEN 'Open Auction - Seedtag'
            WHEN product_type LIKE 'P%' THEN 'PMP Web - O&O'
            WHEN product_type LIKE 'D%' THEN 'Direct Web - O&O'
            WHEN product_type LIKE 'Curation%' THEN 'PMP - Curation'
          END AS business_line
        , CASE
            WHEN channel_id IN ('Sovrn','Sharethrough','Rubicon','OpenX','Pubmatic','AppNexus','ImproveDigital','LoopMe','Adform','OneTag','AdYouLike') THEN 'Reseller'
            WHEN channel_id LIKE 'Smart%' THEN 'Reseller'
            WHEN channel_id IN ('DBM','GDN','Sportradar','StackAdapt','NextRoll','AdMixerBidswitch') THEN 'BidSwitch'
            WHEN channel_id IN ('RtbHouse','TheTradeDesk','Outbrain','StackAdaptDSP','Nexxen','Opera','NextRollPAAPI','Viant','Beeswax','Illumin') THEN 'Direct'
          END AS connection_type
        , SUM(r.net_imp_paid) / 1000.0 AS rev_gross
    FROM st_datalakehouse.analytics.stg_ssp_responses_daily r
    LEFT JOIN st_datalakehouse.analytics.bidder_dsp_mapping b
        ON r.bidder_id = b.bidder_id AND r.channel_id = b.channel_name
    WHERE 1=1
      AND r.date >= DATE '{date_from}' AND r.date < DATE '{date_to}'
      AND r.channel_id <> 'Beachfront'
    GROUP BY 1, 2, 3, 4, 5, 6
    HAVING SUM(r.net_imp_paid) > 1000

    UNION ALL

    SELECT
        CAST(date_trunc('quarter', a.date) AS date) AS quarter
        , dsp_group_name
        , channel_id
        , split_part(a.adomain, '.', 1) AS adomain
        , business_line
        , connection_type
        , SUM(a.revenue) AS rev_gross
    FROM st_datalakehouse.analytics.reporting_closing_bfm_demand a
    WHERE a.date >= DATE '{date_from}' AND a.date < DATE '{date_to}'
    GROUP BY 1, 2, 3, 4, 5, 6
    HAVING SUM(a.revenue) > 1
)

-- NeuroX scope + merge branches to the report grain
, aggregated AS (
    SELECT
        quarter
        , dsp_group_name
        , channel_id
        , business_line
        , connection_type
        , adomain
        , SUM(rev_gross) AS rev_gross
    FROM consolidated_raw
    WHERE (connection_type IS NULL OR connection_type <> 'Reseller')
      AND (business_line IS NULL OR business_line NOT LIKE '%Direct%')
    GROUP BY 1, 2, 3, 4, 5, 6
)

-- Keep only the head: within each group, the brands that cumulatively account
-- for 90% of the group's revenue (windows over the group WITHOUT adomain).
-- cum_before = revenue of all strictly-larger brands; a row survives while the
-- 90% line hasn't been reached before it, so the crossing brand is kept.
, ranked AS (
    SELECT
        a.*
        , SUM(rev_gross) OVER (
            PARTITION BY quarter, dsp_group_name, channel_id, business_line, connection_type
            ORDER BY rev_gross DESC
            ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
          ) AS cum_before
        , SUM(rev_gross) OVER (
            PARTITION BY quarter, dsp_group_name, channel_id, business_line, connection_type
          ) AS group_rev
    FROM aggregated a
)

SELECT
    quarter
    , dsp_group_name
    , channel_id
    , business_line
    , connection_type
    , adomain
    , rev_gross
FROM ranked
WHERE COALESCE(cum_before, 0) < 0.9 * group_rev
ORDER BY rev_gross DESC
