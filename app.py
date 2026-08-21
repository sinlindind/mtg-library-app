import streamlit as st
from services.gsheets import load_users, register_new_user
from utils.auth import hash_password
from utils.tokens import generate_verification_token
import uuid

st.set_page_config(page_title="MTG Library Manager", layout="wide")

# Initialize session state
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# Sidebar Authentication UI
if not st.session_state.logged_in_user:
    st.title("Welcome to MTG Library Manager")
    # Handle Login / Registration logic calling imported helpers...