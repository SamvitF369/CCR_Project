import numpy as np
from database_connection import load_core_tables
from risk_analytics import build_counterparty_exposure

def run_stress_testing(trades_df, collateral_df, stress_scenarios_df, counterparties_df):
    active_trades_df = trades_df[trades_df["trade_status"] == "active"].copy()

    stressed_trades_df = active_trades_df.merge(stress_scenarios_df, on="asset_class", how="inner")
    stressed_trades_df["stressed_exposure"] = stressed_trades_df["mtm_exposure"] * stressed_trades_df["shock_factor"]

    stressed_df = (
        stressed_trades_df.groupby(
            ["scenario_id", "scenario_name", "scenario_type", "severity", "counterparty_id"],
            as_index=False
        )
        .agg(
            mtm_exposure=("mtm_exposure", "sum"),
            stressed_exposure=("stressed_exposure", "sum")
        )
        .merge(
            collateral_df.groupby("counterparty_id", as_index=False).agg(collateral_posted=("collateral_posted", "sum")),
            on="counterparty_id",
            how="left"
        )
        .merge(
            counterparties_df[["counterparty_id", "counterparty_name", "credit_rating", "sector", "country"]],
            on="counterparty_id",
            how="left"
        )
    )

    stressed_df["collateral_posted"] = stressed_df["collateral_posted"].fillna(0)
    stressed_df["stress_loss"] = stressed_df["stressed_exposure"] - stressed_df["collateral_posted"]
    stressed_df["margin_insufficiency"] = np.maximum(stressed_df["stress_loss"], 0)

    return stressed_df.sort_values("stress_loss", ascending=False)

def counterparty_default_simulation(counterparty_exposure_df):
    default_df = counterparty_exposure_df.copy()
    default_df["default_loss"] = np.maximum(default_df["net_exposure"], 0)

    return default_df.sort_values("default_loss", ascending=False)

def rating_downgrade_impact(counterparty_exposure_df):
    rating_addons = {
        "AAA": 0.02,
        "AA": 0.03,
        "A": 0.05,
        "BBB": 0.08,
        "BB": 0.12,
        "B": 0.18
    }

    impact_df = counterparty_exposure_df.copy()
    impact_df["downgrade_margin_addon_rate"] = impact_df["credit_rating"].map(rating_addons).fillna(0.10)
    impact_df["downgrade_margin_addon"] = impact_df["gross_exposure"] * impact_df["downgrade_margin_addon_rate"]

    return impact_df.sort_values("downgrade_margin_addon", ascending=False)

if __name__ == "__main__":
    counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df = load_core_tables()

    counterparty_exposure_df = build_counterparty_exposure(
        counterparties_df,
        trades_df,
        collateral_df,
        margin_calls_df
    )

    stressed_results_df = run_stress_testing(
        trades_df,
        collateral_df,
        stress_scenarios_df,
        counterparties_df
    )

    default_simulation_df = counterparty_default_simulation(counterparty_exposure_df)
    downgrade_impact_df = rating_downgrade_impact(counterparty_exposure_df)

    print(stressed_results_df.head(20))
    print(default_simulation_df.head(10))
    print(downgrade_impact_df.head(10))