import streamlit as st
import pandas as pd
import ssl
from sqlalchemy import create_engine

# Pull DSN from Streamlit secrets (make sure it has no ?sslmode=require)
DB_DSN = st.secrets["db"]["dsn"]

@st.cache_data(ttl=300)
def load_data(days: int = 7):
    """Fetch species logins for the last N days directly from species_logins."""

    # RDS CA
    ssl_context = ssl.create_default_context(cafile="rds-ca.pem")

    # Create engine with pg8000 and SSL context
    engine = create_engine(DB_DSN, connect_args={"ssl_context": ssl_context})

    # Debug line to confirm driver
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
st.title("Species Logins")

days = st.slider("Select number of days", 1, 30, 7)
df = load_data(days)

if df.empty:
    st.warning("No data available yet. Waiting for bot inserts...")
else:
    st.dataframe(df)
    st.line_chart(df.pivot(index="day", columns="species", values="count"))