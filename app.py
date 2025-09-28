import streamlit as st
import pandas as pd
from sqlalchemy import create_engine

DB_DSN = st.secrets["db"]["dsn"]

@st.cache_data(ttl=300)
def load_data(days: int = 7):
    """Fetch species logins for the last N days directly from species_logins."""
    # Explicitly force pg8000 driver (Really annoying Streamlit issue)
    engine = create_engine(DB_DSN, connect_args={"sslmode": "require"})
    st.write(f"Dialect: {engine.dialect.name}, Driver: {engine.dialect.driver}")  # Debug line

    query = """
        SELECT date_trunc('day', ts) AS day,
               species,
               COUNT(*) AS count
        FROM public.species_logins
        WHERE ts >= NOW() - INTERVAL %s
        GROUP BY 1, 2
        ORDER BY 1 ASC, 2 ASC
    """
    df = pd.read_sql(query, engine, params=(f"{days} days",))
    return df

# --- Streamlit UI ---
st.title("Species Logins")

days = st.slider("Select number of days", 1, 30, 7)
df = load_data(days)

if df.empty:
    st.warning("No data available yet. Waiting for bot inserts...")
else:
    st.dataframe(df)
    st.line_chart(df.pivot(index="day", columns="species", values="count"))