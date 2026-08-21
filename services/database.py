import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_supabase() -> Client:
    """Initializes and caches the Supabase client connection."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# --- USER OPERATIONS ---
def register_user(username: str, email: str, password_hash: str, token: str):
    data = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "verification_token": token,
        "is_verified": False
    }
    response = supabase.table("users").insert(data).execute()
    return response.data

def get_user_by_username(username: str):
    response = supabase.table("users").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None

# --- COLLECTION OPERATIONS ---
def get_user_collection(user_id: str):
    response = supabase.table("collection").select("*").eq("user_id", user_id).execute()
    return response.data