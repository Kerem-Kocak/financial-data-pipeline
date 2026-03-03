"""
Streamlit Dashboard — Financial Data Pipeline
----------------------------------------------
Interactive visualization of cryptocurrency market snapshots
stored in the MySQL database.

Launch:
    streamlit run dashboard.py
"""

import os
import streamlit as st
import pandas as pd
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    """Fetch all market snapshots joined with asset names."""
    connection = mysql.connector.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
    )
    query = """
        SELECT
            a.symbol                AS Symbol,
            a.name                  AS Asset,
            s.price_usd             AS Price,
            s.price_change_pct      AS 'Change (%)',
            s.market_cap_usd        AS 'Market Cap',
            s.dominance_pct         AS 'Dominance (%)',
            s.total_blocks          AS Blocks,
            s.snapshot_time          AS Timestamp
        FROM market_snapshots s
        JOIN assets a ON s.asset_id = a.asset_id
        ORDER BY s.snapshot_time DESC;
    """
    df = pd.read_sql(query, connection)
    connection.close()
    return df

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Crypto Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Crypto Market Dashboard")
st.caption("Live data pulled from the Financial Data Pipeline")

# ---------------------------------------------------------------------------
# Load & display
# ---------------------------------------------------------------------------

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not connect to the database: {e}")
    st.stop()

if df.empty:
    st.warning("No snapshots found. Run `python pipeline.py` first.")
    st.stop()

# --- Sidebar filters -------------------------------------------------------
assets = df["Asset"].unique().tolist()
selected = st.sidebar.multiselect("Filter by asset", assets, default=assets)
filtered = df[df["Asset"].isin(selected)]

# --- KPI cards (latest snapshot per asset) ----------------------------------
st.subheader("Latest Snapshot")
latest = filtered.drop_duplicates(subset="Asset", keep="first")

cols = st.columns(len(latest))
for col, (_, row) in zip(cols, latest.iterrows()):
    with col:
        st.metric(
            label=f"{row['Asset']} ({row['Symbol']})",
            value=f"${row['Price']:,.2f}",
            delta=f"{row['Change (%)']:.2f}%" if pd.notna(row['Change (%)']) else None,
        )

# --- Price history chart ----------------------------------------------------
st.subheader("Price History")
chart_data = filtered.pivot_table(
    index="Timestamp", columns="Asset", values="Price"
).sort_index()

st.line_chart(chart_data)

# --- Raw data table ---------------------------------------------------------
st.subheader("All Snapshots")
st.dataframe(filtered, use_container_width=True, hide_index=True)

# --- Footer -----------------------------------------------------------------
st.divider()
st.caption(f"Total records: {len(filtered)} | Assets tracked: {len(assets)}")
