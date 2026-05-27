import streamlit as st
from database_connection import load_core_tables
from risk_analytics import (
    build_counterparty_exposure,
    calculate_portfolio_kpis,
    concentration_by_dimension,
    exposure_threshold_breaches,
    calculate_saccr_exposure
)
from stress_testing import run_stress_testing, rating_downgrade_impact


def to_crores(value):
    return float(value) / 10_000_000


def format_inr_crores(value):
    return f"INR {to_crores(value):,.2f} Cr"


def safe_columns(dataframe, columns):
    return [column for column in columns if column in dataframe.columns]


def convert_money_columns_to_crores(dataframe):
    money_keywords = [
        "exposure",
        "notional",
        "collateral",
        "margin",
        "loss",
        "ead",
        "pfe",
        "addon",
        "cost",
        "score",
        "amount"
    ]

    converted_df = dataframe.copy()

    for column in converted_df.columns:
        if any(keyword in column.lower() for keyword in money_keywords):
            converted_df[column] = converted_df[column].astype(float) / 10_000_000

    return converted_df


def rename_money_columns_to_crores(dataframe):
    renamed_columns = {}

    money_keywords = [
        "exposure",
        "notional",
        "collateral",
        "margin",
        "loss",
        "ead",
        "pfe",
        "addon",
        "cost",
        "score",
        "amount"
    ]

    for column in dataframe.columns:
        if any(keyword in column.lower() for keyword in money_keywords):
            renamed_columns[column] = f"{column}_cr"

    return dataframe.rename(columns=renamed_columns)


def prepare_display_dataframe(dataframe):
    display_df = convert_money_columns_to_crores(dataframe)
    display_df = rename_money_columns_to_crores(display_df)

    return display_df


st.set_page_config(
    page_title="CCR Project Risk Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("CCR Project: Counterparty Credit Risk and CCP Exposure Analytics")

counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df = load_core_tables()

counterparty_exposure_df = build_counterparty_exposure(
    counterparties_df,
    trades_df,
    collateral_df,
    margin_calls_df
)

saccr_df = calculate_saccr_exposure(
    trades_df,
    collateral_df,
    counterparties_df
)

with st.sidebar:
    st.header("Filters")

    selected_sector = st.selectbox(
        "Sector",
        ["All"] + sorted(counterparty_exposure_df["sector"].dropna().unique().tolist())
    )

    selected_country = st.selectbox(
        "Country",
        ["All"] + sorted(counterparty_exposure_df["country"].dropna().unique().tolist())
    )

    selected_rating = st.selectbox(
        "Credit Rating",
        ["All"] + sorted(counterparty_exposure_df["credit_rating"].dropna().unique().tolist())
    )

    selected_severity = st.selectbox(
        "Stress Severity",
        ["Severe", "High", "Moderate"]
    )

filtered_exposure_df = counterparty_exposure_df.copy()
filtered_saccr_df = saccr_df.copy()

if selected_sector != "All":
    filtered_exposure_df = filtered_exposure_df[filtered_exposure_df["sector"] == selected_sector]
    filtered_saccr_df = filtered_saccr_df[filtered_saccr_df["sector"] == selected_sector]

if selected_country != "All":
    filtered_exposure_df = filtered_exposure_df[filtered_exposure_df["country"] == selected_country]
    filtered_saccr_df = filtered_saccr_df[filtered_saccr_df["country"] == selected_country]

if selected_rating != "All":
    filtered_exposure_df = filtered_exposure_df[filtered_exposure_df["credit_rating"] == selected_rating]
    filtered_saccr_df = filtered_saccr_df[filtered_saccr_df["credit_rating"] == selected_rating]

if filtered_exposure_df.empty:
    st.warning("No counterparties match the selected filters.")
    st.stop()

kpis = calculate_portfolio_kpis(filtered_exposure_df)

gross_exposure = kpis["gross_exposure"]
net_exposure = kpis["net_exposure"]
largest_counterparty_exposure = kpis["largest_counterparty_exposure"]
concentration_ratio = kpis["concentration_ratio"]
margin_utilization = kpis["margin_utilization"]
collateral_coverage_ratio = kpis.get("collateral_coverage_ratio", 0)

kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5, kpi_col6 = st.columns(6)

kpi_col1.metric("Gross Exposure", format_inr_crores(gross_exposure))
kpi_col2.metric("Net Exposure", format_inr_crores(net_exposure))
kpi_col3.metric("Largest CP", format_inr_crores(largest_counterparty_exposure))
kpi_col4.metric("Concentration", f"{concentration_ratio:.2%}")
kpi_col5.metric("Margin Util.", f"{margin_utilization:.2f}x")
kpi_col6.metric("Collateral", f"{collateral_coverage_ratio:.2%}")

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

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Exposure Monitor", "Stress Testing", "Concentration", "SA-CCR", "Exports"]
)

with tab1:
    st.subheader("Counterparty Exposure")

    exposure_columns = safe_columns(
        filtered_exposure_df,
        [
            "counterparty_name",
            "credit_rating",
            "sector",
            "country",
            "mtm_exposure",
            "gross_exposure",
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
    )

    exposure_display_df = prepare_display_dataframe(filtered_exposure_df[exposure_columns])

    st.dataframe(
        exposure_display_df,
        use_container_width=True,
        hide_index=True,
        height=520
    )

    st.subheader("Top Counterparty Exposure")

    exposure_chart_df = (
        filtered_exposure_df
        .sort_values("mtm_exposure", ascending=False)
        .head(10)
        .set_index("counterparty_name")[["mtm_exposure", "net_exposure", "collateral_posted"]]
        / 10_000_000
    )

    st.bar_chart(exposure_chart_df, use_container_width=True, height=420)

with tab2:
    st.subheader("Stress Testing")

    scenario_df = stress_scenarios_df[stress_scenarios_df["severity"] == selected_severity]

    stressed_results_df = run_stress_testing(
        trades_df,
        collateral_df,
        scenario_df,
        counterparties_df
    )

    if selected_sector != "All":
        stressed_results_df = stressed_results_df[stressed_results_df["sector"] == selected_sector]

    if selected_country != "All":
        stressed_results_df = stressed_results_df[stressed_results_df["country"] == selected_country]

    if selected_rating != "All":
        stressed_results_df = stressed_results_df[stressed_results_df["credit_rating"] == selected_rating]

    if stressed_results_df.empty:
        st.warning("No stress results match the selected filters.")
    else:
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
        margin_insufficiency = float(stressed_summary_df["margin_insufficiency"].sum())

        stress_col1, stress_col2, stress_col3 = st.columns(3)

        stress_col1.metric("Stressed Exposure", format_inr_crores(stressed_exposure))
        stress_col2.metric("Stress Loss", format_inr_crores(stress_loss))
        stress_col3.metric("Margin Insufficiency", format_inr_crores(margin_insufficiency))

        stress_chart_df = (
            stressed_summary_df
            .set_index("scenario_name")[["mtm_exposure", "stressed_exposure", "stress_loss"]]
            / 10_000_000
        )

        st.bar_chart(stress_chart_df, use_container_width=True, height=420)

        stress_columns = safe_columns(
            stressed_results_df,
            [
                "scenario_name",
                "scenario_type",
                "severity",
                "counterparty_name",
                "credit_rating",
                "sector",
                "country",
                "mtm_exposure",
                "stressed_exposure",
                "collateral_posted",
                "stress_loss",
                "margin_insufficiency"
            ]
        )

        stress_display_df = prepare_display_dataframe(stressed_results_df[stress_columns].head(100))

        st.dataframe(
            stress_display_df,
            use_container_width=True,
            hide_index=True,
            height=520
        )

with tab3:
    concentration_col1, concentration_col2 = st.columns(2)

    with concentration_col1:
        st.subheader("Sector Concentration")

        sector_df = concentration_by_dimension(filtered_exposure_df, "sector")
        sector_chart_df = sector_df.set_index("sector")[["gross_exposure", "net_exposure"]] / 10_000_000
        st.bar_chart(sector_chart_df, use_container_width=True, height=360)
        st.dataframe(prepare_display_dataframe(sector_df), use_container_width=True, hide_index=True, height=300)

        st.subheader("Rating Concentration")

        rating_df = concentration_by_dimension(filtered_exposure_df, "credit_rating")
        rating_chart_df = rating_df.set_index("credit_rating")[["gross_exposure", "net_exposure"]] / 10_000_000
        st.bar_chart(rating_chart_df, use_container_width=True, height=360)
        st.dataframe(prepare_display_dataframe(rating_df), use_container_width=True, hide_index=True, height=300)

    with concentration_col2:
        st.subheader("Country Concentration")

        country_df = concentration_by_dimension(filtered_exposure_df, "country")
        country_chart_df = country_df.set_index("country")[["gross_exposure", "net_exposure"]] / 10_000_000
        st.bar_chart(country_chart_df, use_container_width=True, height=360)
        st.dataframe(prepare_display_dataframe(country_df), use_container_width=True, hide_index=True, height=300)

        st.subheader("Rating Downgrade Impact")

        downgrade_impact_df = rating_downgrade_impact(filtered_exposure_df)
        st.dataframe(
            prepare_display_dataframe(downgrade_impact_df.head(20)),
            use_container_width=True,
            hide_index=True,
            height=360
        )

with tab4:
    st.subheader("SA-CCR Style Exposure")

    if filtered_saccr_df.empty:
        st.warning("No SA-CCR results match the selected filters.")
    else:
        total_saccr_ead = filtered_saccr_df["saccr_ead"].sum()
        total_replacement_cost = filtered_saccr_df["replacement_cost"].sum()
        total_pfe_addon = filtered_saccr_df["pfe_addon"].sum()

        saccr_col1, saccr_col2, saccr_col3 = st.columns(3)

        saccr_col1.metric("SA-CCR EAD", format_inr_crores(total_saccr_ead))
        saccr_col2.metric("Replacement Cost", format_inr_crores(total_replacement_cost))
        saccr_col3.metric("PFE Add-On", format_inr_crores(total_pfe_addon))

        saccr_chart_df = (
            filtered_saccr_df
            .sort_values("saccr_ead", ascending=False)
            .head(10)
            .set_index("counterparty_name")[["replacement_cost", "pfe_addon", "saccr_ead"]]
            / 10_000_000
        )

        st.bar_chart(saccr_chart_df, use_container_width=True, height=420)

        saccr_columns = safe_columns(
            filtered_saccr_df,
            [
                "counterparty_name",
                "credit_rating",
                "sector",
                "country",
                "mtm_exposure",
                "notional_amount",
                "collateral_posted",
                "replacement_cost",
                "pfe_addon",
                "alpha",
                "saccr_ead"
            ]
        )

        saccr_display_df = prepare_display_dataframe(filtered_saccr_df[saccr_columns])

        st.dataframe(
            saccr_display_df,
            use_container_width=True,
            hide_index=True,
            height=520
        )

with tab5:
    st.subheader("Exports")

    st.download_button(
        "Export Filtered Exposure CSV",
        filtered_exposure_df.to_csv(index=False),
        file_name="ccr_filtered_exposure.csv",
        mime="text/csv"
    )

    st.download_button(
        "Export SA-CCR CSV",
        filtered_saccr_df.to_csv(index=False),
        file_name="ccr_saccr_exposure.csv",
        mime="text/csv"
    )

    st.download_button(
        "Export Stress Scenarios CSV",
        stress_scenarios_df.to_csv(index=False),
        file_name="ccr_stress_scenarios.csv",
        mime="text/csv"
    )