import pandas as pd
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)

queries = {

    "gross_exposure": """
        SELECT
            SUM(mtm_exposure) AS gross_exposure
        FROM trades
        WHERE trade_status = 'active'
    """,
    "net_exposure_by_counterparty": """
        WITH trade_exposure AS (
            SELECT
                counterparty_id,
                SUM(mtm_exposure) AS mtm_exposure
            FROM trades
            WHERE trade_status = 'active'
            GROUP BY counterparty_id
        ),
        collateral_balance AS (
            SELECT
                counterparty_id,
                SUM(collateral_posted) AS collateral_posted
            FROM collateral
            GROUP BY counterparty_id
        )
        SELECT
            c.counterparty_id,
            c.counterparty_name,
            c.credit_rating,
            c.sector,
            c.country,
            te.mtm_exposure,
            COALESCE(cb.collateral_posted, 0) AS collateral_posted,
            te.mtm_exposure - COALESCE(cb.collateral_posted, 0) AS net_exposure
        FROM trade_exposure te
        JOIN counterparties c ON c.counterparty_id = te.counterparty_id
        LEFT JOIN collateral_balance cb ON cb.counterparty_id = te.counterparty_id
        ORDER BY net_exposure DESC
    """,
    "exposure_by_sector": """
        SELECT
            c.sector,
            SUM(t.mtm_exposure) AS gross_exposure,
            COUNT(DISTINCT c.counterparty_id) AS counterparty_count
        FROM trades t
        JOIN counterparties c ON c.counterparty_id = t.counterparty_id
        WHERE t.trade_status = 'active'
        GROUP BY c.sector
        ORDER BY gross_exposure DESC
    """,
    "exposure_by_country": """
        SELECT
            c.country,
            SUM(t.mtm_exposure) AS gross_exposure,
            COUNT(DISTINCT c.counterparty_id) AS counterparty_count
        FROM trades t
        JOIN counterparties c ON c.counterparty_id = t.counterparty_id
        WHERE t.trade_status = 'active'
        GROUP BY c.country
        ORDER BY gross_exposure DESC
    """,
    "exposure_by_asset_class": """
        SELECT
            asset_class,
            SUM(notional_amount) AS total_notional_amount,
            SUM(mtm_exposure) AS gross_exposure,
            AVG(maturity_days) AS average_maturity_days
        FROM trades
        WHERE trade_status = 'active'
        GROUP BY asset_class
        ORDER BY gross_exposure DESC
    """,
    "concentration_ratio": """
        WITH counterparty_exposure AS (
            SELECT
                counterparty_id,
                SUM(mtm_exposure) AS counterparty_exposure
            FROM trades
            WHERE trade_status = 'active'
            GROUP BY counterparty_id
        ),
        portfolio AS (
            SELECT
                MAX(counterparty_exposure) AS largest_counterparty_exposure,
                SUM(counterparty_exposure) AS total_exposure
            FROM counterparty_exposure
        )
        SELECT
            largest_counterparty_exposure,
            total_exposure,
            largest_counterparty_exposure / NULLIF(total_exposure, 0) AS concentration_ratio
        FROM portfolio
    """,
    "stressed_exposure": """
        SELECT
            ss.scenario_id,
            ss.scenario_name,
            ss.scenario_type,
            t.asset_class,
            SUM(t.mtm_exposure) AS gross_exposure,
            ss.shock_factor,
            SUM(t.mtm_exposure * ss.shock_factor) AS stressed_exposure
        FROM trades t
        JOIN stress_scenarios ss ON ss.asset_class = t.asset_class
        WHERE t.trade_status = 'active'
        GROUP BY ss.scenario_id, ss.scenario_name, ss.scenario_type, t.asset_class, ss.shock_factor
        ORDER BY stressed_exposure DESC
    """,
    "margin_utilization": """
        WITH exposure AS (
            SELECT
                counterparty_id,
                SUM(mtm_exposure) AS mtm_exposure
            FROM trades
            WHERE trade_status = 'active'
            GROUP BY counterparty_id
        ),
        margin_balance AS (
            SELECT
                counterparty_id,
                SUM(initial_margin) AS initial_margin,
                SUM(variation_margin) AS variation_margin
            FROM margin_calls
            GROUP BY counterparty_id
        )
        SELECT
            c.counterparty_name,
            e.mtm_exposure,
            mb.initial_margin,
            mb.variation_margin,
            e.mtm_exposure / NULLIF(mb.initial_margin + mb.variation_margin, 0) AS margin_utilization
        FROM exposure e
        JOIN counterparties c ON c.counterparty_id = e.counterparty_id
        JOIN margin_balance mb ON mb.counterparty_id = e.counterparty_id
        ORDER BY margin_utilization DESC
    """,
"saccr_exposure": """
WITH active_trades AS (
SELECT
trade_id,counterparty_id, asset_class,notional_amount,mtm_exposure,maturity_days,
CASE
WHEN asset_class = 'Rates' THEN 0.005
WHEN asset_class = 'FX' THEN 0.04
WHEN asset_class = 'Credit' THEN 0.05
WHEN asset_class = 'Equity' THEN 0.32
WHEN asset_class = 'Commodity' THEN 0.18
ELSE 0.10
END AS supervisory_factor,
LEAST(1, SQRT(maturity_days / 365.0)) AS maturity_factor
FROM trades
WHERE trade_status = 'active'
        ),
trade_addons AS (
SELECT counterparty_id,
SUM(mtm_exposure) AS mtm_exposure,
SUM(notional_amount) AS notional_amount,
SUM(notional_amount * supervisory_factor * maturity_factor) AS pfe_addon
FROM active_trades
GROUP BY counterparty_id
        ),
collateral_balance AS (
SELECT
counterparty_id,
SUM(collateral_posted) AS collateral_posted
FROM collateral
GROUP BY counterparty_id
        )
SELECT c.counterparty_id, c.counterparty_name,c.credit_rating,c.sector, c.country,
ta.mtm_exposure,
ta.notional_amount,
COALESCE(cb.collateral_posted, 0) AS collateral_posted,
GREATEST(ta.mtm_exposure - COALESCE(cb.collateral_posted, 0), 0) AS replacement_cost,
ta.pfe_addon,
1.4 AS alpha,
1.4 * (GREATEST(ta.mtm_exposure - COALESCE(cb.collateral_posted, 0), 0)+ ta.pfe_addon) AS saccr_ead
        FROM trade_addons ta
        JOIN counterparties c ON c.counterparty_id = ta.counterparty_id
        LEFT JOIN collateral_balance cb ON cb.counterparty_id = ta.counterparty_id
        ORDER BY saccr_ead DESC
    """
}

for query_name, query in queries.items():
    dataframe = pd.read_sql_query(text(query), engine)
    print("\n")
    print(query_name)
    print(dataframe.head(10))