import numpy as np
from database_connection import load_core_tables

def build_counterparty_exposure(counterparties_df, trades_df, collateral_df, margin_calls_df):
    active_trades_df = trades_df[trades_df["trade_status"] == "active"].copy()

    trade_exposure_df = (
        active_trades_df.groupby("counterparty_id", as_index=False)
        .agg(
            mtm_exposure=("mtm_exposure", "sum"),
            notional_amount=("notional_amount", "sum"),
            maturity_days=("maturity_days", "mean")
        )
    )

    collateral_balance_df = (
        collateral_df.groupby("counterparty_id", as_index=False)
        .agg(collateral_posted=("collateral_posted", "sum"))
    )

    margin_balance_df = (
        margin_calls_df.groupby("counterparty_id", as_index=False)
        .agg(
            initial_margin=("initial_margin", "sum"),
            variation_margin=("variation_margin", "sum")
        )
    )

    exposure_df = (
        counterparties_df
        .merge(trade_exposure_df, on="counterparty_id", how="left")
        .merge(collateral_balance_df, on="counterparty_id", how="left")
        .merge(margin_balance_df, on="counterparty_id", how="left")
    )

    exposure_df[["mtm_exposure", "notional_amount", "collateral_posted", "initial_margin", "variation_margin"]] = exposure_df[
        ["mtm_exposure", "notional_amount", "collateral_posted", "initial_margin", "variation_margin"]
    ].fillna(0)

    exposure_df["gross_exposure"] = exposure_df["mtm_exposure"]
    exposure_df["net_exposure"] = exposure_df["mtm_exposure"] - exposure_df["collateral_posted"]

    margin_resources = exposure_df["initial_margin"] + exposure_df["variation_margin"]
    exposure_df["margin_utilization"] = np.where(
        margin_resources > 0,
        exposure_df["mtm_exposure"] / margin_resources,
        0
    )

    exposure_df["collateral_coverage_ratio"] = np.where(
        exposure_df["mtm_exposure"] > 0,
        exposure_df["collateral_posted"] / exposure_df["mtm_exposure"],
        0
    )

    exposure_df["ead_estimate"] = np.maximum(exposure_df["net_exposure"], 0)

    exposure_df["pfe_estimate"] = (
        exposure_df["mtm_exposure"]
        * np.sqrt(exposure_df["maturity_days"].fillna(365) / 365)
        * 0.18
    )

    exposure_df["risk_score"] = (
        exposure_df["ead_estimate"] * 0.45
        + exposure_df["pfe_estimate"] * 0.35
        + np.maximum(exposure_df["margin_utilization"] - 1, 0) * exposure_df["mtm_exposure"] * 0.20
    )

    return exposure_df.sort_values("risk_score", ascending=False)

def calculate_portfolio_kpis(counterparty_exposure_df):
    gross_exposure = float(counterparty_exposure_df["mtm_exposure"].sum())
    net_exposure = float(counterparty_exposure_df["net_exposure"].sum())
    largest_counterparty_exposure = float(counterparty_exposure_df["mtm_exposure"].max())
    total_exposure = gross_exposure

    concentration_ratio = (
        largest_counterparty_exposure / total_exposure
        if total_exposure else 0
    )

    margin_denominator = (
        counterparty_exposure_df["initial_margin"].sum()
        + counterparty_exposure_df["variation_margin"].sum()
    )

    margin_utilization = (
        gross_exposure / margin_denominator
        if margin_denominator else 0
    )

    collateral_coverage_ratio = (
        counterparty_exposure_df["collateral_posted"].sum() / gross_exposure
        if gross_exposure else 0
    )

    return {
        "gross_exposure": gross_exposure,
        "net_exposure": net_exposure,
        "largest_counterparty_exposure": largest_counterparty_exposure,
        "concentration_ratio": concentration_ratio,
        "margin_utilization": margin_utilization,
        "collateral_coverage_ratio": collateral_coverage_ratio
    }

def concentration_by_dimension(counterparty_exposure_df, dimension):
    grouped_df = (
        counterparty_exposure_df.groupby(dimension, as_index=False)
        .agg(
            gross_exposure=("mtm_exposure", "sum"),
            net_exposure=("net_exposure", "sum"),
            collateral_posted=("collateral_posted", "sum"),
            counterparty_count=("counterparty_id", "nunique")
        )
        .sort_values("gross_exposure", ascending=False)
    )

    grouped_df["concentration_ratio"] = grouped_df["gross_exposure"] / grouped_df["gross_exposure"].sum()

    return grouped_df

def exposure_threshold_breaches(counterparty_exposure_df):
    breaches_df = counterparty_exposure_df.copy()
    breaches_df["limit_utilization"] = breaches_df["mtm_exposure"] / breaches_df["risk_limit"]

    return breaches_df[breaches_df["limit_utilization"] > 1].sort_values("limit_utilization", ascending=False)

if __name__ == "__main__":
    counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df = load_core_tables()

    counterparty_exposure_df = build_counterparty_exposure(
        counterparties_df,
        trades_df,
        collateral_df,
        margin_calls_df
    )

    kpis = calculate_portfolio_kpis(counterparty_exposure_df)

    print(counterparty_exposure_df.head(15))
    print(kpis)
    print(concentration_by_dimension(counterparty_exposure_df, "sector"))
    print(concentration_by_dimension(counterparty_exposure_df, "country"))
    print(exposure_threshold_breaches(counterparty_exposure_df))