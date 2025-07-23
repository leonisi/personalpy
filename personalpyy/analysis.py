import pandas as pd
import plotly.express as px
import sqlite3
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = os.getenv("DATABASE_URL", "finance.db")

def get_transactions_df():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    return df

def plot_expenses_by_category():
    df = get_transactions_df()
    if df.empty:
        return None
    cat_sum = df.groupby('category')['amount'].sum().reset_index()
    fig = px.pie(cat_sum, names='category', values='amount', title='Expenses by Category')
    return fig

def plot_balance_over_time():
    df = get_transactions_df()
    if df.empty:
        return None
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['balance'] = df['amount'].cumsum()
    fig = px.line(df, x='date', y='balance', title='Balance Over Time')
    return fig
