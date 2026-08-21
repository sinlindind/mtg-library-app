import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Creates and caches the Supabase connection."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = get_supabase_client()

# --- USER OPERATIONS ---

def create_user(username: str, email: str, password_hash: str, salt: str, token: str):
    """Inserts a new unverified user into the Supabase 'users' table."""
    data = {
        "username": username,
        "email": email.lower().strip(),
        "password_hash": f"{password_hash}:{salt}", # Combined hash and salt
        "is_verified": False,
        "verification_token": token
    }
    response = supabase.table("users").insert(data).execute()
    return response.data

def get_user_by_username(username: str):
    """Fetches a user record by username."""
    response = supabase.table("users").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None

def get_user_by_email(email: str):
    """Fetches a user record by email."""
    response = supabase.table("users").select("*").eq("email", email.lower().strip()).execute()
    return response.data[0] if response.data else None

def verify_user_email(email: str):
    """Updates a user's status to verified."""
    response = supabase.table("users").update({
        "is_verified": True,
        "verification_token": None
    }).eq("email", email.lower().strip()).execute()
    return response.data

# --- COLLECTION OPERATIONS ---

def get_user_collection(user_id: str):
    """Fetches all cards in a user's collection."""
    response = supabase.table("collection").select("*").eq("user_id", user_id).execute()
    return response.data