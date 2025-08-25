import streamlit as st
import pandas as pd

# ---- Safe helpers ----
def sort_safe(df: pd.DataFrame, by):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    cols = set(df.columns)
    if isinstance(by, str):
        by = [by]
    keys = [c for c in by if c in cols]
    return df.sort_values(keys) if keys else df

def list_from_state(state, key):
    try:
        val = state.get(key, [])
        return val if isinstance(val, (list, tuple)) else []
    except Exception:
        return []

def toast_ok(msg: str):
    st.success(msg, icon="✅")

def toast_error(msg: str):
    st.error(msg, icon="⚠️")

def table(df: pd.DataFrame, use_container_width=True, height=360):
    st.dataframe(df if isinstance(df, pd.DataFrame) else pd.DataFrame(),
                 use_container_width=use_container_width, height=height)
