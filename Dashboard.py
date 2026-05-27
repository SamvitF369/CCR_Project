import streamlit as st
from database_connection import load_core_tables
from risk_analytics import (
    build_counterparty_exposure,
    calculate_portfolio_kpis,
    concentration_by_dimension,
    exposure_threshold_breaches
)
from stress_testing import run_stress_testing, rating_downgrade_impact

def format_inr(value):
    value = float(value)

    if abs(value) >= 10_000_000:
        return f"INR {value / 10_000_000:,.2f} Cr"

    if abs(value) >= 100_000:
        return f"INR {value / 100_000:,.2f} L"

    return f"INR {value:,.0f}"

st.set_page_config(page_title="CCR Project Risk Monitor", layout="wide")

st.title("CCR Project: Counterparty Credit Risk and CCP Exposure Analytics")

counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df = load_core_tables()

counterparty_exposure_df = build_counterparty_exposure(
    counterparties_df,
    trades_df,
    collateral_df,
    margin_calls_df
)

with st.sidebar:
    selected_sector = st.selectbox("Sector", ["All"] + sorted(counterparty_exposure_df["sector"].dropna().unique().tolist()))
    selected_country = st.selectbox("Country", ["All"] + sorted(counterparty_exposure_df["country"].dropna().unique().tolist()))
    selected_rating = st.selectbox("Credit Rating", ["All"] + sorted(counterparty_exposure_df["credit_rating"].dropna().unique().tolist()))
    selected_severity = st.selectbox("Stress Severity", ["Severe", "High", "Moderate"])

filtered_exposure_df = counterparty_exposure_df.copy()

if selected_sector != "All":
    filtered_exposure_df = filtered_exposure_df[filtered_exposure_df["sector"] == selected_sector]

if selected_country != "All":
    filtered_exposure_df = filtered_exposure_df[filtered_exposure_df["country"] == selected_country]

if selected_rating != "All":
    filtered_exposure_df = filtered_exposure_df[filtered_exposure_df["credit_rating"] == selected_rating]

kpis = calculate_portfolio_kpis(filtered_exposure_df)

gross_exposure = kpis["gross_exposure"]
net_exposure = kpis["net_exposure"]
largest_counterparty_exposure = kpis["largest_counterparty_exposure"]
concentration_ratio = kpis["concentration_ratio"]
margin_utilization = kpis["margin_utilization"]
collateral_coverage_ratio = kpis["collateral_coverage_ratio"]

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

col1.metric("Gross Exposure", format_inr(gross_exposure))
col2.metric("Net Exposure", format_inr(net_exposure))
col3.metric("Largest Counterparty", format_inr(largest_counterparty_exposure))
col4.metric("Concentration Ratio", f"{concentration_ratio:.2%}")
col5.metric("Margin Utilization", f"{margin_utilization:.2f}x")
col6.metric("Collateral Coverage", f"{collateral_coverage_ratio:.2%}")

breaches_df = exposure_threshold_breaches(filtered_exposure_df)

alert_messages = []

if concentration_ratio > 0.20:
    alert_messages.append("Single-counterparty concentration is above 20%")

if margin_utilization > 1.50:
    alert_messages.append("Margin utilization is above 1.50x")

if collateral_coverage_ratio < 0.75:
    alert_messages.append("Collateral coverage is below 75%")

if not breaches_df.empty:
    alert_messages.append(f"{len(breaches_df)} counterparties exceed approved risk limits")

if alert_messages:
    st.error(" | ".join(alert_messages))
else:
    st.success("No critical risk alerts")

tab1, tab2, tab3, tab4 = st.tabs(["Exposure Monitor", "Stress Testing", "Concentration", "Exports"])

with tab1:
    st.subheader("Top Counterparty Exposures")

    display_df = filtered_exposure_df[
        [
            "counterparty_name",
            "credit_rating",
            "sector",
            "country",
            "mtm_exposure",
            "collateral_posted",
            "net_exposure",
            "initial_margin",
            "variation_margin",
            "margin_utilization",
            "collateral_coverage_ratio",
            "ead_estimate",
            "pfe_estimate",
            "risk_score"
        ]
    ].copy()

    st.dataframe(display_df, width=True, hide_index=True)

    chart_df = (
        filtered_exposure_df
        .sort_values("mtm_exposure", ascending=False)
        .head(10)
        .set_index("counterparty_name")[["mtm_exposure", "net_exposure", "collateral_posted"]]
    )

    st.bar_chart(chart_df)

with tab2:
    scenario_df = stress_scenarios_df[stress_scenarios_df["severity"] == selected_severity]

    stressed_results_df = run_stress_testing(
        trades_df,
        collateral_df,
        scenario_df,
        counterparties_df
    )

    stressed_summary_df = (
        stressed_results_df.groupby("scenario_name", as_index=False)
        .agg(
            mtm_exposure=("mtm_exposure", "sum"),
            stressed_exposure=("stressed_exposure", "sum"),
            stress_loss=("stress_loss", "sum"),
            margin_insufficiency=("margin_insufficiency", "sum")
        )
        .sort_values("stress_loss", ascending=False)
    )

    stressed_exposure = float(stressed_summary_df["stressed_exposure"].sum())
    stress_loss = float(stressed_summary_df["stress_loss"].sum())

    stress_col1, stress_col2 = st.columns(2)

    stress_col1.metric("Stressed Exposure", format_inr(stressed_exposure))
    stress_col2.metric("Stress Loss", format_inr(stress_loss))

    stress_chart_df = stressed_summary_df.set_index("scenario_name")[["mtm_exposure", "stressed_exposure", "stress_loss"]]
    st.bar_chart(stress_chart_df)

    st.dataframe(stressed_results_df.head(30), width=True, hide_index=True)

with tab3:
    sector_df = concentration_by_dimension(filtered_exposure_df, "sector")
    country_df = concentration_by_dimension(filtered_exposure_df, "country")
    rating_df = concentration_by_dimension(filtered_exposure_df, "credit_rating")
    downgrade_impact_df = rating_downgrade_impact(filtered_exposure_df)

    st.subheader("Sector Concentration")
    st.bar_chart(sector_df.set_index("sector")[["gross_exposure", "net_exposure"]])
    st.dataframe(sector_df,width=True, hide_index=True)

    st.subheader("Country Concentration")
    st.bar_chart(country_df.set_index("country")[["gross_exposure", "net_exposure"]])
    st.dataframe(country_df, width=True, hide_index=True)

    st.subheader("Rating Concentration")
    st.bar_chart(rating_df.set_index("credit_rating")[["gross_exposure", "net_exposure"]])
    st.dataframe(rating_df, width=True, hide_index=True)

    st.subheader("Rating Downgrade Impact")
    st.dataframe(downgrade_impact_df.head(20), width=True, hide_index=True)

with tab4:
    st.download_button(
        "Export Filtered Exposure CSV",
        filtered_exposure_df.to_csv(index=False),
        file_name="ccr_filtered_exposure.csv",
        mime="text/csv"
    )

    st.download_button(
        "Export Stress Scenarios CSV",
        stress_scenarios_df.to_csv(index=False),
        file_name="ccr_stress_scenarios.csv",
        mime="text/csv"
    )