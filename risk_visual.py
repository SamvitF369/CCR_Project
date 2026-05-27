from pathlib import Path
import matplotlib.pyplot as plt
from database_connection import load_core_tables
from risk_analytics import build_counterparty_exposure, concentration_by_dimension
from stress_testing import run_stress_testing

CHART_DIR = Path("charts")
CHART_DIR.mkdir(exist_ok=True)

def apply_style():
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#2f3a45",
        "axes.labelcolor": "#1f2933",
        "xtick.color": "#1f2933",
        "ytick.color": "#1f2933",
        "axes.titleweight": "bold"
    })

def save_bar_chart(dataframe, x_column, y_column, title, filename):
    apply_style()

    plot_df = dataframe.sort_values(y_column, ascending=True).tail(12)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(plot_df[x_column], plot_df[y_column], color="#2f6f8f")
    ax.set_title(title)
    ax.set_xlabel("INR Exposure")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHART_DIR / filename, dpi=150)
    plt.close(fig)

def save_rating_distribution(counterparty_exposure_df):
    apply_style()

    rating_df = counterparty_exposure_df["credit_rating"].value_counts().reset_index()
    rating_df.columns = ["credit_rating", "count"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(rating_df["credit_rating"], rating_df["count"], color="#5b8c85")
    ax.set_title("Rating Distribution")
    ax.set_xlabel("Credit Rating")
    ax.set_ylabel("Counterparty Count")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "rating_distribution.png", dpi=150)
    plt.close(fig)

def save_stressed_vs_normal_chart(stressed_results_df):
    apply_style()

    stressed_summary_df = (
        stressed_results_df.groupby("scenario_name", as_index=False)
        .agg(
            mtm_exposure=("mtm_exposure", "sum"),
            stressed_exposure=("stressed_exposure", "sum")
        )
        .sort_values("stressed_exposure", ascending=False)
        .head(10)
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(stressed_summary_df["scenario_name"], stressed_summary_df["mtm_exposure"], label="Normal Exposure", color="#5b8c85")
    ax.bar(stressed_summary_df["scenario_name"], stressed_summary_df["stressed_exposure"], alpha=0.65, label="Stressed Exposure", color="#b85c38")
    ax.set_title("Stressed vs Normal Exposure")
    ax.set_ylabel("INR Exposure")
    ax.tick_params(axis="x", rotation=45)
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(CHART_DIR / "stressed_vs_normal_exposure.png", dpi=150)
    plt.close(fig)

if __name__ == "__main__":
    counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df = load_core_tables()

    counterparty_exposure_df = build_counterparty_exposure(
        counterparties_df,
        trades_df,
        collateral_df,
        margin_calls_df
    )

    sector_df = concentration_by_dimension(counterparty_exposure_df, "sector")
    country_df = concentration_by_dimension(counterparty_exposure_df, "country")

    stressed_results_df = run_stress_testing(
        trades_df,
        collateral_df,
        stress_scenarios_df,
        counterparties_df
    )

    save_bar_chart(counterparty_exposure_df, "counterparty_name", "gross_exposure", "Exposure by Counterparty", "exposure_by_counterparty.png")
    save_bar_chart(sector_df, "sector", "gross_exposure", "Sector Exposure", "sector_exposure.png")
    save_bar_chart(country_df, "country", "gross_exposure", "Country Exposure", "country_exposure.png")
    save_bar_chart(counterparty_exposure_df, "counterparty_name", "net_exposure", "Top Risky Counterparties", "top_risky_counterparties.png")
    save_rating_distribution(counterparty_exposure_df)
    save_stressed_vs_normal_chart(stressed_results_df)

    print("Risk visualizations complete")