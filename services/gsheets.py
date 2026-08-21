import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_worksheet(worksheet_name: str):
    creds_dict = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sh = client.open_by_url(creds_dict["spreadsheet"])
    return sh.worksheet(worksheet_name)

def load_users() -> pd.DataFrame:
    try:
        ws = get_worksheet("Users")
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty or "username" not in df.columns:
            return pd.DataFrame(columns=["user_id", "username", "email", "password_hash", "is_verified", "verification_token"])
        return df
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return pd.DataFrame()

def register_new_user(user_id: str, username: str, email: str, password_hash: str, token: str):
    ws = get_worksheet("Users")
    # Append user matching your updated Google Sheet schema
    ws.append_row([user_id, username, email, password_hash, False, token])