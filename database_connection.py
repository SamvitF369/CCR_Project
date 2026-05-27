import pandas as pd
from sqlalchemy import create_engine, text
from config import SQLALCHEMY_DATABASE_URL

def get_engine():
    return create_engine(SQLALCHEMY_DATABASE_URL)

def read_query(query):
    engine = get_engine()

    with engine.connect() as connection:
        return pd.read_sql_query(text(query), connection)

def load_core_tables():
    engine = get_engine()

    counterparties_df = pd.read_sql_query("SELECT * FROM counterparties", engine)
    trades_df = pd.read_sql_query("SELECT * FROM trades", engine)
    collateral_df = pd.read_sql_query("SELECT * FROM collateral", engine)
    margin_calls_df = pd.read_sql_query("SELECT * FROM margin_calls", engine)
    market_data_df = pd.read_sql_query("SELECT * FROM market_data", engine)
    stress_scenarios_df = pd.read_sql_query("SELECT * FROM stress_scenarios", engine)

    return counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df

if __name__ == "__main__":
    counterparties_df, trades_df, collateral_df, margin_calls_df, market_data_df, stress_scenarios_df = load_core_tables()

    print(counterparties_df.head())
    print(trades_df.head())
    print(collateral_df.head())
    print(margin_calls_df.head())
    print(market_data_df.head())
    print(stress_scenarios_df.head())