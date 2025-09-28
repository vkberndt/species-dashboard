import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Page setup
st.set_page_config(page_title="Species Login Trends", page_icon="🦖", layout="wide")
st.title("🦖 Species Login Trends")
st.caption("Daily counts of species logged into the server (UTC)")

# Database connection string comes from Streamlit Cloud secrets
DB_DSN = st.secrets["db"]["dsn"]

@st.cache_data(ttl=300)
def load_data(days: int):
    """Fetch daily species counts from Supabase."""
    conn = psycopg2.connect(DB_DSN, cursor_factory=RealDictCursor)
    with conn.cursor() as cur:
        # If you created the materialized view daily_species_counts:
        cur.execute("""
            SELECT day, species, count
            FROM public.daily_species_counts
            WHERE day >= NOW() - INTERVAL %s
            ORDER BY day ASC, species ASC
        """, (f"{days} days",))
        rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows)

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    days = st.slider("Days to display", 7, 180, 60)

df = load_data(days)

if df.empty:
    st.warning("No data found for the selected range. Try increasing the days or check DB population.")
else:
    all_species = sorted(df["species"].unique())
    selected = st.multiselect("Species", all_species, default=all_species)

    df = df[df["species"].isin(selected)]
    pivot = df.pivot(index="day", columns="species", values="count").fillna(0)

    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Stacked area (trend)")
        st.area_chart(pivot, height=320)
    with col2:
        st.subheader("Daily totals by species (bar)")
        st.bar_chart(pivot, height=320)

    # Data table
    st.subheader("Daily counts (table)")
    st.dataframe(pivot.astype(int), use_container_width=True)

    # Totals
    st.subheader("Totals in range")
    totals = pivot.sum()
    for sp, val in totals.items():
        st.metric(label=sp, value=int(val))