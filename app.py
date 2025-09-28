import streamlit as st
import pandas as pd
import ssl
from sqlalchemy import create_engine

# DSN is stored in .streamlit/secrets.toml
DB_DSN = st.secrets["db"]["dsn"]

@st.cache_data(ttl=300)
def load_data(days: int = 7):
    """Fetch species logins for the last N days directly from species_logins."""

    # Use the Supabase-provided CA cert (prod-ca-2021.crt)
    ssl_context = ssl.create_default_context(cafile="prod-ca-2021.crt")

    # Create engine with pg8000 and pinned SSL context
    engine = create_engine(DB_DSN, connect_args={"ssl_context": ssl_context})

    # Debug line to confirm dialect/driver
    st.write(f"Dialect: {engine.dialect.name}, Driver: {engine.dialect.driver}")

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
st.title("🦖 Species Logins")

days = st.slider("Select number of days", 1, 30, 7)
df = load_data(days)

if df.empty:
    st.warning("No data available yet. Waiting for bot inserts...")
else:
    st.dataframe(df)
    st.line_chart(df.pivot(index="day", columns="species", values="count"))