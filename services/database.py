import streamlit as st
from supabase import create_client, Client

# Initialize Supabase client
@st.cache_resource
def init_supabase() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# ==========================================
# User Functions
# ==========================================

def create_user(username: str, email: str, password_hash: str, salt: str, verification_token: str = None):
    """Inserts a new user record."""
    data = {
        "username": username,
        "email": email,
        "password_hash": f"{password_hash}:{salt}",
        "verification_token": verification_token
    }
    response = supabase.table("users").insert(data).execute()
    return response.data[0] if response.data else None


def get_user_by_username(username: str):
    """Fetches user record by username."""
    response = supabase.table("users").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None


def get_user_by_email(email: str):
    """Fetches user record by email."""
    response = supabase.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None


def verify_user_email(email: str):
    """Updates user record status when email is verified."""
    response = supabase.table("users").update({"is_verified": True}).eq("email", email).execute()
    return response.data[0] if response.data else None


# ==========================================
# Library Functions
# ==========================================

def add_card_to_library(user_id: int, scryfall_id: str, finish: str, quantity: int, condition: str, purchase_price: float = None):
    """Adds a card item to the user library."""
    data = {
        "user_id": user_id,
        "scryfall_id": scryfall_id,
        "finish": finish,
        "quantity": quantity,
        "condition": condition,
        "purchase_price": purchase_price
    }
    response = supabase.table("library").insert(data).execute()
    return response.data[0] if response.data else None


def get_user_library(user_id: int):
    """Fetches all items in user library."""
    response = supabase.table("library").select("*").eq("user_id", user_id).execute()
    return response.data if response.data else []