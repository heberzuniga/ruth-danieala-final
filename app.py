import streamlit as st
import pandas as pd

from config import APP_TITLE, APP_VERSION, DEFAULTS
from ui.moderator import render_moderator
from ui.participant import render_participant
from ui.components import list_from_state

st.set_page_config(page_title=APP_TITLE, layout="wide")

# Init state defaults
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

st.title(f"{APP_TITLE} · v{APP_VERSION}")

with st.sidebar:
    st.header("Controles")
    role = st.selectbox("Rol", ["Moderador","Participante"], index=0)
    game_code = st.text_input("Game Code", value="MB-001")
    st.caption("Para demo no es necesario Google Sheets.")

# Router
if role == "Moderador":
    render_moderator(st.session_state)
else:
    render_participant(st.session_state)

st.divider()
st.caption("Demo MVP — Cálculo local con CSV. Integración con Google Sheets en la siguiente iteración.")
