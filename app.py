import streamlit as st
import pandas as pd
import ssl
from sqlalchemy import create_engine

DB_DSN = st.secrets["db"]["dsn"]

@st.cache_data(ttl=300)
def load_data(days: int = 7):
    ssl_context = ssl.create_default_context(cafile="prod-ca-2021.crt")
    engine = create_engine(DB_DSN, connect_args={"ssl_context": ssl_context})

    query = """
        SELECT date_trunc('day', ts) AS day,
               species,
               COUNT(*) AS count
        FROM public.species_logins
        WHERE ts >= NOW() - make_interval(days := %s)
        GROUP BY 1, 2
        ORDER BY 1 ASC, 2 ASC
    """
    df = pd.read_sql(query, engine, params=(days,))
    return df

# --- Streamlit UI ---
st.title("🦖 Species Logins")

days = st.slider("Select number of days", 1, 30, 7)
df = load_data(days)

if df.empty:
    st.warning("No data available yet. Waiting for bot inserts...")
else:
    # --- Species distribution chart (total counts) ---
    st.subheader("Species distribution (total logins)")
    species_totals = df.groupby("species")["count"].sum().reset_index()
    species_totals = species_totals.sort_values("count", ascending=False)

    st.bar_chart(species_totals.set_index("species"))

    # --- Time series chart (sorted species order) ---
    st.subheader("Logins over time (species ranked by total)")
    # Pivot for line chart
    pivoted = df.pivot(index="day", columns="species", values="count").fillna(0)

    # Reorder columns by total counts
    species_order = species_totals["species"].tolist()
    pivoted = pivoted[species_order]

    st.line_chart(pivoted)