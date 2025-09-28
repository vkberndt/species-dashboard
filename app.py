import streamlit as st
import pandas as pd
import ssl
import matplotlib.pyplot as plt
from sqlalchemy import create_engine

DB_DSN = st.secrets["db"]["dsn"]

@st.cache_data(ttl=300)
def load_species_data(days: int = 7):
    """Fetch species logins for the last N days."""
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
    return pd.read_sql(query, engine, params=(days,))

@st.cache_data(ttl=300)
def load_diet_data(days: int = 7):
    """Fetch carnivore vs herbivore totals via join with species_diets."""
    ssl_context = ssl.create_default_context(cafile="prod-ca-2021.crt")
    engine = create_engine(DB_DSN, connect_args={"ssl_context": ssl_context})

    query = """
        SELECT d.diet,
               SUM(l.count) AS total_count
        FROM (
            SELECT date_trunc('day', ts) AS day,
                   species,
                   COUNT(*) AS count
            FROM public.species_logins
            WHERE ts >= NOW() - make_interval(days := %s)
            GROUP BY 1, 2
        ) l
        JOIN public.species_diets d ON l.species = d.species
        GROUP BY d.diet
        ORDER BY total_count DESC;
    """
    return pd.read_sql(query, engine, params=(days,))

# --- Streamlit UI ---
st.title("🦖 Species Logins Dashboard")

days = st.slider("Select number of days", 1, 30, 7)

# Species-level data
df_species = load_species_data(days)

if df_species.empty:
    st.warning("No data available yet. Waiting for bot inserts...")
else:
    # --- Species distribution bar chart ---
    st.subheader("Species distribution (total logins)")
    species_totals = df_species.groupby("species")["count"].sum().reset_index()
    species_totals = species_totals.sort_values("count", ascending=False)

    st.bar_chart(species_totals.set_index("species"))

    # --- Leaderboard split by diet ---
    st.subheader("Top 5 Herbivores and Carnivores")

    # Pull the diet lookup table once
    ssl_context = ssl.create_default_context(cafile="prod-ca-2021.crt")
    engine = create_engine(DB_DSN, connect_args={"ssl_context": ssl_context})
    diet_lookup = pd.read_sql("SELECT species, diet FROM public.species_diets", engine)

    # Merge species totals with diet classification
    species_with_diet = species_totals.merge(diet_lookup, on="species", how="left")

    # Top 5 herbivores
    st.markdown("### 🥦 Top 5 Herbivores")
    top_herbivores = (
        species_with_diet[species_with_diet["diet"] == "herbivore"]
        .sort_values("count", ascending=False)
        .head(5)
    )
    for _, row in top_herbivores.iterrows():
        st.write(f"**{row['species']}** — {row['count']} logins")

    # Top 5 carnivores
    st.markdown("### 🍖 Top 5 Carnivores")
    top_carnivores = (
        species_with_diet[species_with_diet["diet"] == "carnivore"]
        .sort_values("count", ascending=False)
        .head(5)
    )
    for _, row in top_carnivores.iterrows():
        st.write(f"**{row['species']}** — {row['count']} logins")

    # --- Carnivore vs Herbivore pie chart ---
    st.subheader("Carnivores vs Herbivores")
    df_diet = load_diet_data(days)

    if not df_diet.empty:
        st.pyplot(
            df_diet.set_index("diet")
                   .plot.pie(y="total_count", autopct="%1.1f%%", legend=False)
                   .figure
        )