import streamlit as st
from supabase import create_client, Client

# Initialize the Supabase client using Streamlit secrets
@st.cache_resource
def init_supabase() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# ==========================================
# User Functions
# ==========================================

def create_user(username: str, email: str, password_hash: str, salt: str):
    """Inserts a new user into the users table."""
    data = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "salt": salt,
    }
    response = supabase.table("users").insert(data).execute()
    return response.data[0] if response.data else None


def get_user_by_username(username: str):
    """Fetches a single user record by username."""
    response = supabase.table("users").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None


def get_user_by_email(email: str):
    """Fetches a single user record by email."""
    response = supabase.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None


def verify_user_login(username: str):
    """Helper to fetch a user record for password verification."""
    return get_user_by_username(username)


# ==========================================
# Library / Card Functions
# ==========================================

def add_card_to_library(user_id: int, card_data: dict):
    """Adds a card record linked to a specific user_id."""
    data = {"user_id": user_id, **card_data}
    response = supabase.table("library").insert(data).execute()
    return response.data[0] if response.data else None


def get_user_library(user_id: int):
    """Retrieves all cards stored in a user's library."""
    response = (
        supabase.table("library")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return response.data if response.data else []