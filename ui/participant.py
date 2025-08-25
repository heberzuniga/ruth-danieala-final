import streamlit as st
import pandas as pd
from ui.components import sort_safe, table

def render_participant(state: dict):
    st.subheader("Panel del Participante")
    team = st.text_input("Nombre del equipo", key="team_name")
    st.caption("Registra tu equipo y observa precios publicados por el Moderador")

    ronda_actual = state.get("ronda_actual", 1)
    prices = state.get("prices", [])
    dfp = pd.DataFrame([p for p in prices if p.get("ronda")==ronda_actual])
    dfp = sort_safe(dfp, "bond_id")
    st.markdown("**Precios publicados (ronda actual)**")
    table(dfp)
    st.info("Ejecución de órdenes llegará en la siguiente iteración (UI + almacenamiento).")
