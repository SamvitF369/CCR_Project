from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from config import SQLALCHEMY_DATABASE_URL

DATA_DIR = Path("data")
RANDOM_SEED = 42

def generate_synthetic_data(as_of_date="2026-05-26"):
    rng = np.random.default_rng(RANDOM_SEED)
    as_of_date = pd.Timestamp(as_of_date)

    counterparty_names = [
        "HDFC Bank Treasury",
        "ICICI Securities",
        "Axis Bank Global Markets",
        "State Bank of India Markets",
        "Kotak Mahindra Capital",
        "Reliance Treasury Services",
        "Tata Capital Markets",
        "Aditya Birla Finance",
        "Bajaj Finance Treasury",
        "Mahindra Financial Services",
        "SBI Pension Fund",
        "LIC Investment Desk",
        "Nippon India Asset Management",
        "Mirae Asset India",
        "DSP Investment Managers",
        "IIFL Securities",
        "Motilal Oswal Financial Services",
        "Edelweiss Financial Services",
        "Power Finance Corporation",
        "REC Limited Treasury"
    ]

    counterparties_df = pd.DataFrame({
        "counterparty_id": range(1, len(counterparty_names) + 1),
        "counterparty_name": counterparty_names,
        "credit_rating": rng.choice(["AAA", "AA", "A", "BBB", "BB", "B"], len(counterparty_names), p=[0.08, 0.20, 0.32, 0.25, 0.12, 0.03]),
        "sector": rng.choice(["Bank", "Broker Dealer", "Asset Manager", "NBFC", "Insurance", "Corporate Treasury", "Pension Fund"], len(counterparty_names)),
        "country": ["India"] * len(counterparty_names),
        "legal_entity_type": rng.choice(["Bank", "NBFC", "Fund", "Corporate", "Broker Dealer"], len(counterparty_names)),
        "onboarding_date": as_of_date - pd.to_timedelta(rng.integers(365, 3650, len(counterparty_names)), unit="D"),
        "risk_limit": rng.integers(750_000_000, 7_500_000_000, len(counterparty_names)).astype(float),
        "is_clearing_member": rng.choice([True, False], len(counterparty_names), p=[0.40, 0.60])
    })

    asset_classes = ["Rates", "Credit", "FX", "Equity", "Commodity"]

    product_map = {
        "Rates": ["INR Interest Rate Swap", "MIBOR OIS Swap", "Government Bond Future"],
        "Credit": ["Corporate Bond CDS", "Credit Index Swap"],
        "FX": ["USDINR Forward", "USDINR Option", "Cross Currency Swap"],
        "Equity": ["Nifty Index Future", "Bank Nifty Option", "Equity Swap"],
        "Commodity": ["Gold Futures Swap", "Crude Oil Swap", "Commodity Option"]
    }

    trade_rows = []

    for trade_id in range(1, 501):
        asset_class = rng.choice(asset_classes, p=[0.35, 0.15, 0.25, 0.15, 0.10])
        notional_amount = float(rng.lognormal(mean=np.log(450_000_000), sigma=0.80))
        mtm_exposure = max(notional_amount * rng.normal(loc=0.025, scale=0.05), 0)

        trade_rows.append({
            "trade_id": trade_id,
            "counterparty_id": int(rng.integers(1, len(counterparty_names) + 1)),
            "asset_class": asset_class,
            "product_type": rng.choice(product_map[asset_class]),
            "trade_date": as_of_date - pd.to_timedelta(int(rng.integers(1, 900)), unit="D"),
            "maturity_days": int(rng.integers(30, 3650)),
            "currency": rng.choice(["INR", "USD", "EUR", "GBP", "JPY"], p=[0.72, 0.18, 0.04, 0.03, 0.03]),
            "notional_amount": round(notional_amount, 2),
            "mtm_exposure": round(mtm_exposure, 2),
            "trade_status": rng.choice(["active", "matured"], p=[0.94, 0.06])
        })

    trades_df = pd.DataFrame(trade_rows)

    active_exposure = trades_df[trades_df["trade_status"] == "active"].groupby("counterparty_id")["mtm_exposure"].sum()

    collateral_rows = []
    margin_rows = []

    for counterparty_id in counterparties_df["counterparty_id"]:
        mtm_exposure = float(active_exposure.get(counterparty_id, 0))
        collateral_posted = max(mtm_exposure * rng.normal(0.82, 0.18), 0)
        initial_margin = max(mtm_exposure * rng.normal(0.30, 0.08), 10_000_000)
        variation_margin = max(mtm_exposure * rng.normal(0.16, 0.06), 0)

        collateral_rows.append({
            "collateral_id": int(counterparty_id),
            "counterparty_id": int(counterparty_id),
            "collateral_type": rng.choice(["Cash INR", "Government Securities", "Corporate Bond", "Bank Guarantee"], p=[0.55, 0.25, 0.15, 0.05]),
            "currency": "INR",
            "collateral_posted": round(collateral_posted, 2),
            "haircut_rate": round(float(rng.uniform(0.01, 0.12)), 4),
            "valuation_date": as_of_date
        })

        margin_rows.append({
            "margin_call_id": int(counterparty_id),
            "counterparty_id": int(counterparty_id),
            "call_date": as_of_date,
            "initial_margin": round(initial_margin, 2),
            "variation_margin": round(variation_margin, 2),
            "margin_call_status": rng.choice(["Settled", "Pending", "Disputed"], p=[0.75, 0.20, 0.05]),
            "due_date": as_of_date + pd.Timedelta(days=1),
            "amount_disputed": round(float(max(rng.normal(0, 2_500_000), 0)), 2)
        })

    collateral_df = pd.DataFrame(collateral_rows)
    margin_calls_df = pd.DataFrame(margin_rows)

    market_rows = []

    for asset_class in asset_classes:
        for days_back in range(90):
            market_rows.append({
                "asset_class": asset_class,
                "market_date": as_of_date - pd.Timedelta(days=days_back),
                "market_factor": f"{asset_class} India Risk Factor",
                "factor_level": round(float(rng.normal(100, 8)), 6),
                "volatility": round(float(rng.uniform(0.08, 0.42)), 6),
                "currency": "INR"
            })

    market_data_df = pd.DataFrame(market_rows)

    scenario_rows = []
    scenario_id = 1

    scenario_templates = [
        ("Base Volatility Shock", "Volatility Shock", 1.15, "Moderate"),
        ("Liquidity Stress", "Liquidity Shock", 1.35, "High"),
        ("Systemic Default Event", "Default Shock", 1.75, "Severe")
    ]

    for asset_class in asset_classes:
        for scenario_name, scenario_type, shock_factor, severity in scenario_templates:
            scenario_rows.append({
                "scenario_id": scenario_id,
                "scenario_name": f"{asset_class} {scenario_name}",
                "scenario_type": scenario_type,
                "asset_class": asset_class,
                "shock_factor": shock_factor,
                "stress_loss": 0.0,
                "scenario_horizon_days": 30 if severity == "Severe" else 10,
                "severity": severity
            })
            scenario_id += 1

    stress_scenarios_df = pd.DataFrame(scenario_rows)

    exposure_snapshots_df = (
        trades_df[trades_df["trade_status"] == "active"]
        .groupby("counterparty_id", as_index=False)
        .agg(gross_exposure=("mtm_exposure", "sum"))
        .merge(collateral_df[["counterparty_id", "collateral_posted"]], on="counterparty_id", how="left")
        .merge(margin_calls_df[["counterparty_id", "initial_margin", "variation_margin"]], on="counterparty_id", how="left")
    )

    exposure_snapshots_df["snapshot_date"] = as_of_date
    exposure_snapshots_df["net_exposure"] = exposure_snapshots_df["gross_exposure"] - exposure_snapshots_df["collateral_posted"]
    exposure_snapshots_df["stress_loss"] = np.maximum(exposure_snapshots_df["gross_exposure"] * 1.75 - exposure_snapshots_df["collateral_posted"], 0)

    exposure_snapshots_df = exposure_snapshots_df[
        [
            "counterparty_id",
            "snapshot_date",
            "gross_exposure",
            "collateral_posted",
            "net_exposure",
            "initial_margin",
            "variation_margin",
            "stress_loss"
        ]
    ]

    return {
        "counterparties": counterparties_df,
        "trades": trades_df,
        "collateral": collateral_df,
        "margin_calls": margin_calls_df,
        "market_data": market_data_df,
        "stress_scenarios": stress_scenarios_df,
        "exposure_snapshots": exposure_snapshots_df
    }

def export_csvs(dataframes):
    DATA_DIR.mkdir(exist_ok=True)

    for table_name, dataframe in dataframes.items():
        dataframe.to_csv(DATA_DIR / f"{table_name}.csv", index=False)

def insert_to_postgresql(dataframes):
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

    insert_order = [
        "counterparties",
        "trades",
        "collateral",
        "margin_calls",
        "market_data",
        "stress_scenarios",
        "exposure_snapshots"
    ]

    with engine.begin() as connection:
        connection.exec_driver_sql(
            "TRUNCATE TABLE exposure_snapshots, stress_scenarios, market_data, margin_calls, collateral, trades, counterparties CASCADE"
        )

        for table_name in insert_order:
            dataframes[table_name].to_sql(table_name, connection, if_exists="append", index=False)

if __name__ == "__main__":
    dataframes = generate_synthetic_data()
    export_csvs(dataframes)
    insert_to_postgresql(dataframes)
    print("Data generation complete")