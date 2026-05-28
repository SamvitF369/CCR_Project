**CCR Project**

Counterparty Credit Risk and CCP Exposure Analytics platform using PostgreSQL, Python, SQL, Streamlit, Excel, and Jupyter Notebook.

This project simulates a simplified risk analytics system used by banks, clearing members, CCPs, treasury desks, and derivatives risk teams for counterparty exposure monitoring, collateral analysis, margin analytics, stress testing, concentration risk monitoring, default simulation, Excel reporting, and dashboard reporting.

**Database Name**

The PostgreSQL database name must be exactly:CCR Project

**Technology Stack**

PostgreSQL,pgAdmin,Python,pandas,numpy,matplotlib,SQLAlchemy,psycopg2,Jupyter Notebook,Streamlit,Excel,openpyxl,xlsxwriter
**Project Structure**

CCR_Project/,config.py,requirements.txt,data_generation.py,sql_risk_analytics.py,database_connection.py,risk_analytics.py
stress_testing.py,risk_visual.py,Excel.py,Dashboard.py,README.md,SQL code,sql/analytics_queries.sql,notebooks/CCR_Project_Workflow.ipynb,data/,charts/,reports/

**Core Database Tables**
counterparties,trades,collateral,margin_calls,market_data,stress_scenarios,exposure_snapshots,Core Primary Keys,counterparty_id,trade_id,collateral_id,margin_call_id,scenario_id

**Core Risk Fields**

counterparty_name,credit_rating,sector,country,asset_class,notional_amount,mtm_exposure,net_exposure,collateral_posted,initial_margin,variation_margin,stress_loss,shock_factor,maturity_days,trade_date

**Core Python DataFrames**

counterparties_df,trades_df,collateral_df,margin_calls_df,market_data_df,stress_scenarios_df,counterparty_exposure_df,stressed_results_df,saccr_df

**Core Risk Formulas**

net_exposure = mtm_exposure - collateral_posted
stressed_exposure = mtm_exposure * shock_factor
concentration_ratio = largest_counterparty_exposure / total_exposure
margin_utilization = gross_exposure / (initial_margin + variation_margin)
collateral_coverage_ratio = collateral_posted / mtm_exposure

**SA-CCR Style Exposure Logic**

The project includes a simplified SA-CCR-style exposure calculation.
replacement_cost = max(mtm_exposure - collateral_posted, 0)
asset_class_addon = notional_amount * supervisory_factor * maturity_factor
pfe_addon = sum(asset_class_addon)
saccr_ead = 1.4 * (replacement_cost + pfe_addon)

**Supervisory Factor Assumptions**

Rates: 0.005
FX: 0.040
Credit: 0.050
Equity: 0.320
Commodity: 0.180
Stress Scenario Assumptions
Moderate Volatility Shock: 1.15
High Liquidity Shock: 1.35
Severe Default Shock: 1.75
**Main Components**

1. Configuration
configuration.py stores PostgreSQL connection settings.

The SQLAlchemy connection uses the database name CCR Project.

Before running locally, update the PostgreSQL password in configuration.py.



2. Data Generation
data_generation.py creates realistic synthetic Indian institutional counterparty and derivatives exposure data.

Generated datasets include counterparties, trades, collateral balances, margin calls, market data, stress scenarios, and exposure snapshots.

The synthetic data is loaded into PostgreSQL, which acts as the source of truth for downstream analytics.

3. SQL Risk Analytics
sql_risk_analytics.py runs SQL analytics directly against PostgreSQL.

Analytics include gross exposure, net exposure, exposure by counterparty, exposure by sector, exposure by country, exposure by asset class, largest counterparties, concentration ratio, stressed exposure, margin utilization, and simplified SA-CCR exposure.

This file demonstrates database-side analytics using SQL queries, joins, aggregations, CTEs, and ranking logic.

4. Database Connection Layer
database_connection.py provides reusable PostgreSQL connection and table loading logic using SQLAlchemy and pandas.

It loads the core tables into pandas DataFrames for downstream Python analytics.

5. Python Risk Analytics Engine
risk_analytics.py provides reusable Python analytics functions for counterparty exposure calculation, portfolio KPI calculation, net exposure, collateral coverage, margin utilization, exposure-at-default estimate, potential future exposure estimate, concentration analysis, risk limit breaches, and simplified SA-CCR exposure.

This file powers the Streamlit dashboard, Excel report, and Jupyter notebook.

6. Stress Testing Engine
stress_testing.py runs stress testing and scenario analytics.

Stress testing includes market shock simulation, stressed exposure, stress loss, margin insufficiency, counterparty default simulation, and rating downgrade impact.

7. Visualizations
risk_visualizations.py generates matplotlib charts for exposure by counterparty, sector exposure, country exposure, top risky counterparties, rating distribution, and stressed vs normal exposure.

Charts are saved in the charts folder.

8. Excel Reporting
excel_reporting.py generates a business-friendly Excel report.

The Excel report includes portfolio KPIs, counterparty exposure, sector concentration, country concentration, rating concentration, stress summary, stress details, limit breaches, downgrade impact, SA-CCR exposure, trades, collateral, and margin calls.

The report is saved in the reports folder.

9. Streamlit Dashboard
streamlit_dashboard.py provides an interactive dashboard for risk monitoring.

Dashboard features include KPI cards, sidebar filters, exposure monitor, stress testing tab, concentration analytics tab, SA-CCR exposure tab, export buttons, and risk alerts.

All dashboard monetary values are shown in INR crores.

10. Jupyter Notebook
notebooks/CCR_Project_Workflow.ipynb provides an analyst-style walkthrough of the project.

The notebook is used to explain data loading, exposure calculations, KPI interpretation, concentration analysis, stress testing results, SA-CCR exposure, charts, and business interpretation.

Setup Instructions
Step 1: Create PostgreSQL Database
Create a PostgreSQL database named exactly CCR Project.

Step 2: Install Dependencies
Run pip install -r requirements.txt.

Step 3: Configure Database Connection
Open configuration.py and update your local PostgreSQL password.

Step 4: Create Database Schema
Run sql/database_schema.sql in pgAdmin Query Tool.

Step 5: Generate And Load Synthetic Data
Run python data_generation.py.

Step 6: Run SQL Analytics
Run python sql_risk_analytics.py.

Step 7: Test Database Connection
Run python database_connection.py.

Step 8: Run Python Risk Analytics
Run python risk_analytics.py.

Step 9: Run Stress Testing
Run python stress_testing.py.

Step 10: Generate Visualizations
Run python risk_visualizations.py.

Step 11: Generate Excel Report
Run python excel_reporting.py.

Step 12: Run Streamlit Dashboard
Run streamlit run streamlit_dashboard.py.

Step 13: Open Jupyter Notebook
Run jupyter notebook and open notebooks/CCR_Project_Workflow.ipynb.


**Dashboard Metrics**

The dashboard displays gross exposure, net exposure, largest counterparty exposure, concentration ratio, margin utilization, collateral coverage, stressed exposure, stress loss, margin insufficiency, SA-CCR EAD, replacement cost, and PFE add-on.


**Risk Alerts**

The dashboard raises alerts when single-counterparty concentration is above 20%, margin utilization is above 1.50x, collateral coverage is below 75%, or counterparties exceed approved risk limits.

These thresholds are simplified internal monitoring assumptions for demonstration.

**Analytics Included**

gross exposure
net exposure
collateral-adjusted exposure
exposure by counterparty
exposure by sector
exposure by country
exposure by asset class
largest counterparty exposure
concentration ratio
margin utilization
collateral coverage
exposure-at-default estimate
potential future exposure estimate
stressed exposure
stress loss
margin insufficiency
rating downgrade impact
simplified SA-CCR exposure
replacement cost
PFE add-on
supervisory factor
maturity factor
SA-CCR EAD
Finance Concepts Demonstrated
counterparty credit risk
mark-to-market exposure
gross exposure
net exposure
collateralized exposure
initial margin
variation margin
margin utilization
collateral coverage
exposure at default
potential future exposure
SA-CCR-style exposure
replacement cost
PFE add-on
supervisory factor
maturity factor
stress testing
stress loss
margin insufficiency
rating downgrade impact
concentration risk
risk limit breaches
**Model Assumptions**

This project uses synthetic data because real institutional counterparty and trade data is confidential.

Key assumptions include Indian institutional counterparties, primarily INR-denominated exposure, lognormal trade notionals, positive MTM exposure modeling, active trades driving current exposure, matured trades being excluded from current exposure analytics, varying collateral coverage by counterparty, simplified benchmark stress shocks, simplified PFE logic, and simplified SA-CCR-style exposure.

**Limitations**

This is a portfolio-grade educational risk analytics platform, not a production regulatory CCR engine.

It does not yet include full SA-CCR regulatory implementation, legal netting sets, ISDA CSA terms, supervisory duration, delta adjustment, maturity bucket aggregation, hedging set aggregation, multiplier effects, Monte Carlo exposure simulation, real derivative pricing, real market data feeds, CVA or DVA, wrong-way risk, backtesting, model validation, production authentication, or production deployment.
