import os

APP_TITLE = "Misión Bonos — MVP"
APP_VERSION = "0.1.0"

# Parámetros globales por defecto
DEFAULTS = {
    "fraccion_anio": 0.25,    # 3 meses por ronda
    "bid_bp": 20,             # 20 bps
    "ask_bp": 20,             # 20 bps
    "comision_bps": 10,       # 10 bps
    "rondas_totales": 6,
    "cash_inicial": 100000.0,
}

# Feature flags
FLAGS = {
    "enable_sheets": True,  # puede estar en False si no hay secretos
}

def has_sheets_secrets():
    try:
        import streamlit as st
        return "gcp_service_account" in st.secrets and "SPREADSHEET_KEY" in st.secrets
    except Exception:
        return False
