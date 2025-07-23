# Personal Finance Tracker & Visualizer

This project is a personal finance tracker and visualizer built with FastAPI, SQLite, pandas, plotly, and more.

## Features
- Add, view, and delete transactions via API
- Store transactions in SQLite
- Data validation with Pydantic
- Unique IDs for users/transactions (uuid)
- Config management with dotenv
- Data analysis and visualization with pandas & plotly
- (Optional) Streamlit dashboard

## Setup
1. Install dependencies:
   ```sh
   pip install fastapi uvicorn pydantic python-dotenv pandas plotly requests sqlite3 streamlit
   ```
2. Create a `.env` file for configuration (see `.env.example`).
3. Run the API:
   ```sh
   uvicorn main:app --reload
   ```
4. (Optional) Run the Streamlit dashboard:
   ```sh
   streamlit run dashboard.py
   ```

## Project Structure
- `main.py` - FastAPI backend
- `models.py` - Pydantic models
- `database.py` - SQLite database logic
- `analysis.py` - Data analysis/visualization
- `dashboard.py` - Streamlit dashboard (optional)
- `.env` - Environment variables
