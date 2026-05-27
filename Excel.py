import pandas as pd
from pathlib import Path
from database_connection import load_core_tables
from risk_analytics import (
    build_counterparty_exposure,
    calculate_portfolio_kpis,
    concentration_by_dimension,
    exposure_threshold_breaches
)
from stress_testing import run_stress_testing, rating_downgrade_impact

OUTPUT_DIR = Path("reports")
OUTPUT_DIR.mkdir(exist_ok=True)

def export_excel_report():
    counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df = load_core_tables()

    counterparty_exposure_df = build_counterparty_exposure(
        counterparties_df,
        trades_df,
        collateral_df,
        margin_calls_df
    )

    kpis = calculate_portfolio_kpis(counterparty_exposure_df)

    kpi_df = pd.DataFrame([kpis])

    sector_concentration_df = concentration_by_dimension(counterparty_exposure_df, "sector")
    country_concentration_df = concentration_by_dimension(counterparty_exposure_df, "country")
    rating_concentration_df = concentration_by_dimension(counterparty_exposure_df, "credit_rating")

    breaches_df = exposure_threshold_breaches(counterparty_exposure_df)

    stressed_results_df = run_stress_testing(
        trades_df,
        collateral_df,
        stress_scenarios_df,
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

    downgrade_impact_df = rating_downgrade_impact(counterparty_exposure_df)

    output_file = OUTPUT_DIR / "CCR_Project_Risk_Report.xlsx"

    with pd.ExcelWriter(output_file, engine="xlsxwriter") as writer:
        kpi_df.to_excel(writer, sheet_name="Portfolio KPIs", index=False)
        counterparty_exposure_df.to_excel(writer, sheet_name="Counterparty Exposure", index=False)
        sector_concentration_df.to_excel(writer, sheet_name="Sector Concentration", index=False)
        country_concentration_df.to_excel(writer, sheet_name="Country Concentration", index=False)
        rating_concentration_df.to_excel(writer, sheet_name="Rating Concentration", index=False)
        stressed_summary_df.to_excel(writer, sheet_name="Stress Summary", index=False)
        stressed_results_df.to_excel(writer, sheet_name="Stress Details", index=False)
        breaches_df.to_excel(writer, sheet_name="Limit Breaches", index=False)
        downgrade_impact_df.to_excel(writer, sheet_name="Downgrade Impact", index=False)
        trades_df.to_excel(writer, sheet_name="Trades", index=False)
        collateral_df.to_excel(writer, sheet_name="Collateral", index=False)
        margin_calls_df.to_excel(writer, sheet_name="Margin Calls", index=False)

        workbook = writer.book

        money_format = workbook.add_format({"num_format": '#,##0'})
        percent_format = workbook.add_format({"num_format": "0.00%"})
        decimal_format = workbook.add_format({"num_format": "0.00"})
        header_format = workbook.add_format({
            "bold": True,
            "bg_color": "#1F4E78",
            "font_color": "white",
            "border": 1
        })

        for sheet_name, worksheet in writer.sheets.items():
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(0, 0, 0, 20)
            worksheet.set_row(0, None, header_format)
            worksheet.set_column(0, 0, 28)
            worksheet.set_column(1, 20, 18, money_format)

        writer.sheets["Portfolio KPIs"].set_column(0, 10, 24, decimal_format)
        writer.sheets["Counterparty Exposure"].set_column("J:J", 18, decimal_format)
        writer.sheets["Counterparty Exposure"].set_column("K:K", 18, percent_format)
        writer.sheets["Sector Concentration"].set_column("E:E", 18, percent_format)
        writer.sheets["Country Concentration"].set_column("E:E", 18, percent_format)
        writer.sheets["Rating Concentration"].set_column("E:E", 18, percent_format)

        exposure_sheet = writer.sheets["Counterparty Exposure"]

        chart = workbook.add_chart({"type": "bar"})
        chart.add_series({
            "name": "Gross Exposure",
            "categories": ["Counterparty Exposure", 1, 1, 10, 1],
            "values": ["Counterparty Exposure", 1, 9, 10, 9]
        })
        chart.set_title({"name": "Top Counterparty Gross Exposure"})
        chart.set_x_axis({"name": "INR Exposure"})
        chart.set_y_axis({"name": "Counterparty"})
        chart.set_style(10)
        exposure_sheet.insert_chart("Q2", chart)

        sector_sheet = writer.sheets["Sector Concentration"]

        sector_chart = workbook.add_chart({"type": "column"})
        sector_chart.add_series({
            "name": "Gross Exposure",
            "categories": ["Sector Concentration", 1, 0, len(sector_concentration_df), 0],
            "values": ["Sector Concentration", 1, 1, len(sector_concentration_df), 1]
        })
        sector_chart.set_title({"name": "Sector Exposure"})
        sector_chart.set_y_axis({"name": "INR Exposure"})
        sector_chart.set_style(10)
        sector_sheet.insert_chart("H2", sector_chart)

        stress_sheet = writer.sheets["Stress Summary"]

        stress_chart = workbook.add_chart({"type": "column"})
        stress_chart.add_series({
            "name": "Stressed Exposure",
            "categories": ["Stress Summary", 1, 0, len(stressed_summary_df), 0],
            "values": ["Stress Summary", 1, 2, len(stressed_summary_df), 2]
        })
        stress_chart.add_series({
            "name": "Stress Loss",
            "categories": ["Stress Summary", 1, 0, len(stressed_summary_df), 0],
            "values": ["Stress Summary", 1, 3, len(stressed_summary_df), 3]
        })
        stress_chart.set_title({"name": "Stress Scenario Results"})
        stress_chart.set_y_axis({"name": "INR Exposure"})
        stress_chart.set_style(10)
        stress_sheet.insert_chart("H2", stress_chart)

    print(f"Excel report created: {output_file}")

if __name__ == "__main__":
    export_excel_report()