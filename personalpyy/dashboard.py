import requests
import streamlit as st
from analysis import get_transactions_df, plot_expenses_by_category, plot_balance_over_time
import sqlite3
import os
from dotenv import load_dotenv
import re
APP_NAME = "FINT"


load_dotenv()
DB_PATH = os.getenv("DATABASE_URL", "finance.db")
API_KEY = os.getenv("API_KEY")

# --- Restore login state from query params if present ---
query_params = st.query_params
uuid_regex = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
if "token" in query_params and query_params["token"]:
    token_candidate = query_params["token"][0]
    if uuid_regex.match(token_candidate):
        st.session_state.token = token_candidate
if "username" in query_params and query_params["username"]:
    st.session_state.username = query_params["username"][0]

# --- User Auth State ---
if "token" not in st.session_state:
    st.session_state.token = None
if "username" not in st.session_state:
    st.session_state.username = None
if "page" not in st.session_state:
    st.session_state.page = "home"

cols = st.columns([3,2,2,3,4])
cols[1].markdown(f'<span style="color:#fff;font-size:1.6rem;font-weight:bold;letter-spacing:2px;">{APP_NAME}</span>', unsafe_allow_html=True)

if st.session_state.token:
    cols[0].markdown(f"Logged in as: <b>{st.session_state.username}</b>", unsafe_allow_html=True)
    if cols[4].button("Logout"):
        st.session_state.token = None
        st.session_state.username = None
        st.session_state.page = "home"
        st.success("Logged out!")
        st.query_params.clear()
else:
    if cols[4].button("Login/Register"):
        st.session_state.page = "login"

if cols[2].button("Home"):
    st.session_state.page = "home"
if cols[3].button("Dashboard"):
    st.session_state.page = "dashboard"
page = st.session_state.page

if page == "home":
    st.title(APP_NAME)
    st.markdown(
        f"""
        ## Hi, I'm Leo and I introduce to you **{APP_NAME}**!
        <br>
        FINT is your personal finance tracker and visualizer. Easily add your expenses, see your spending by category, and track your balance over time.
        <br>
        <br>
        <p style="color:#918e8e;">Someone:  So what's so cool about it?</p>
        <br>
        <p>To much to count but here are some of them:</p>
        <ul style="color:#fff;">
            <li>1. Track your expenses effortlessly</li>
            <li>2. Visualize your spending habits</li>
            <li>3. Gain insights into your financial health</li>
            <li>4. All for free! Just the computer maybe</li>
        </ul>
        <br>
        <br>
        """,
        unsafe_allow_html=True,
    )
    print(DB_PATH)
    if not st.session_state.token:
        st.info("Please login or register to save and view your personal transactions.")
    if st.button("Go to Dashboard"):
        st.session_state.page = "dashboard"
        st.rerun()

elif page == "login":
    st.title("Login or Register")
    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            resp = requests.post("http://127.0.0.1:8000/token", data={"username": login_username, "password": login_password})
            print("Login response JSON:", resp.json())
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                st.session_state.token = token
                st.session_state.username = login_username
                st.success("Logged in!")
                st.query_params.update({"token": token, "username": login_username})
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                try:
                    error_detail = resp.json().get("detail", "Unknown error")
                except Exception:
                    error_detail = resp.text
                st.error("Login failed: " + error_detail)
    with tab2:
        st.subheader("Register")
        reg_username = st.text_input("Username", key="reg_username")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        if st.button("Register"):
            resp = requests.post("http://127.0.0.1:8000/register", json={"username": reg_username, "password": reg_password})
            if resp.status_code == 200:
                st.success("Registration successful! Please login.")
                st.session_state.token = None
                st.session_state.username = None
            else:
                try:
                    error_detail = resp.json().get("detail", "Unknown error")
                except Exception:
                    error_detail = resp.text
                st.error("Registration failed: " + error_detail)

elif page == "dashboard":
    if not st.session_state.token:
        st.warning("You must be logged in to view your dashboard.")
        st.session_state.page = "login"
        st.rerun()
    st.title(f"{APP_NAME} Dashboard")

    # --- Add Transaction Form ---
    st.header("Add a Transaction")
    with st.form("add_transaction_form"):
        date = st.date_input("Date")
        description = st.text_input("Description")
        amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
        category = st.text_input("Category")
        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            if amount < 0:
                st.error("Amount cannot be negative.")
            else:
                # Save transaction via FastAPI
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                tx_data = {
                    "date": date.isoformat(),
                    "description": description,
                    "amount": amount,
                    "category": category
                }
                resp = requests.post("http://127.0.0.1:8000/transactions/", json=tx_data, headers=headers)
                if resp.status_code == 200:
                    st.success("Transaction added!")
                else:
                    try:
                        error_detail = resp.json().get("detail", "Unknown error")
                    except Exception:
                        error_detail = resp.text
                    st.error("Failed to add transaction: " + error_detail)

    # Fetch transactions via FastAPI
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    print("Frontend sending token:", st.session_state.token)
    resp = requests.get("http://127.0.0.1:8000/transactions/", headers=headers)
    if resp.status_code == 200:
        tx_list = resp.json()
        import pandas as pd
        df = pd.DataFrame(tx_list)
        # Ensure correct types for graphing
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df = None
        try:
            error_detail = resp.json().get("detail", "Unknown error")
        except Exception:
            error_detail = resp.text
        st.error(f"Failed to fetch transactions: {error_detail}")

    st.header("All Transactions")
    if df is not None and not df.empty:
        df_display = df.drop(columns=["user_id"], errors="ignore")
        st.dataframe(df_display)
    else:
        st.write("No data to display.")

    st.button("Refresh Data", on_click=lambda: st.rerun())
    def go_to_edit_transactions():
        st.session_state.page = "edit_transactions"

    st.button("Edit Transactions", on_click=go_to_edit_transactions)

    st.header("Expenses by Category")
    if df is not None and not df.empty and "category" in df.columns and "amount" in df.columns:
        st.write("Debug: Transactions DataFrame", df)
        import plotly.express as px
        cat_sum = df.dropna(subset=["category", "amount"]).groupby("category")["amount"].sum().reset_index()
        st.write("Debug: Category Summary", cat_sum)
        if not cat_sum.empty:
            fig1 = px.pie(cat_sum, names="category", values="amount", title="Expenses by Category")
            st.plotly_chart(fig1)
        else:
            st.write("No category data to display.")
    else:
        st.write("No data to display.")

    st.header("Balance Over Time")
    if df is not None and not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df_sorted = df.sort_values("date")
        df_sorted["balance"] = df_sorted["amount"].cumsum()
        fig2 = px.line(df_sorted, x="date", y="balance", title="Balance Over Time")
        st.plotly_chart(fig2)
    else:
        st.write("No data to display.")

    
elif page == "edit_transactions":
    st.title("Edit Transactions")

    st.header("All Transactions")
    # Fetch transactions via FastAPI (to ensure df is available)
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    resp = requests.get("http://127.0.0.1:8000/transactions/", headers=headers)
    if resp.status_code == 200:
        import pandas as pd
        tx_list = resp.json()
        df = pd.DataFrame(tx_list)
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df = None
        try:
            error_detail = resp.json().get("detail", "Unknown error")
        except Exception:
            error_detail = resp.text
        st.error(f"Failed to fetch transactions: {error_detail}")

    if df is not None and not df.empty:
        df_display = df.drop(columns=["user_id"], errors="ignore")
        st.dataframe(df_display)
        st.button("Refresh Data", on_click=lambda: st.rerun())

        st.header("Edit Transactions")
        tx_id = st.selectbox("Select Transaction ID", df["id"].tolist())
        tx_row = df[df["id"] == tx_id]
        if not tx_row.empty:
            date = st.date_input("Date", value=tx_row["date"].dt.date.iloc[0])
            description = st.text_input("Description", value=tx_row["description"].iloc[0])
            amount = st.number_input("Amount", value=tx_row["amount"].iloc[0], min_value=0.0, step=0.01, format="%.2f")
            category = st.text_input("Category", value=tx_row["category"].iloc[0])
            submitted = st.button("Update Transaction")
            delete_confirm = st.checkbox("Are you sure you want to delete this transaction?")
            delete_submitted = st.button("Delete Transaction")
            if submitted:
                if amount < 0:
                    st.error("Amount cannot be negative.")
                else:
                    # Update transaction via FastAPI
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    tx_data = {
                        "date": date.isoformat(),
                        "description": description,
                        "amount": amount,
                        "category": category
                    }
                    resp = requests.put(f"http://127.0.0.1:8000/transactions/{tx_id}", json=tx_data, headers=headers)
                    if resp.status_code == 200:
                        st.success("Transaction updated!")
                    else:
                        try:
                            error_detail = resp.json().get("detail", "Unknown error")
                        except Exception:
                            error_detail = resp.text
                        st.error("Failed to update transaction: " + error_detail)
            if delete_submitted:
                if delete_confirm:
                    headers = {"Authorization": f"Bearer {st.session_state.token}"}
                    resp = requests.delete(f"http://127.0.0.1:8000/transactions/{tx_id}", headers=headers)
                    if resp.status_code == 200:
                        st.success("Transaction deleted!")
                        st.rerun()
                    else:
                        try:
                            error_detail = resp.json().get("detail", "Unknown error")
                        except Exception:
                            error_detail = resp.text
                        st.error("Failed to delete transaction: " + error_detail)
                else:
                    st.warning("Please confirm deletion by checking the box above.")
        else:
            st.write("No data to display.")
    else:
        st.write("No data to display.")
