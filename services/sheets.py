import json
import streamlit as st

def has_secrets():
    return "gcp_service_account" in st.secrets and "SPREADSHEET_KEY" in st.secrets

def get_client():
    import gspread
    from google.oauth2.service_account import Credentials
    info = json.loads(st.secrets["gcp_service_account"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def open_spreadsheet(key_or_url: str):
    if not has_secrets():
        raise RuntimeError("Faltan secretos: gcp_service_account / SPREADSHEET_KEY")
    client = get_client()
    return client.open_by_key(key_or_url) if len(key_or_url) < 60 else client.open_by_url(key_or_url)

# Stubs de lectura/escritura (para implementar en la iteración siguiente)
def read_table(sh, sheet_name: str) -> list[dict]:
    ws = sh.worksheet(sheet_name)
    rows = ws.get_all_records()
    return rows

def clear_and_write(sh, sheet_name: str, header: list[str], rows: list[list]) -> None:
    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        ws = sh.add_worksheet(title=sheet_name, rows=1, cols=len(header))
    ws.clear()
    ws.append_row(header)
    if rows:
        ws.append_rows(rows)

def write_rows_append(sh, sheet_name: str, rows: list[list]) -> None:
    ws = sh.worksheet(sheet_name)
    if rows:
        ws.append_rows(rows)
