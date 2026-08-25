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
# User Cards Functions
# ==========================================

def add_card_to_library(
    user_id: str, 
    scryfall_id: str, 
    finish: str, 
    quantity: int, 
    condition: str = "Near Mint", 
    purchase_price: float = None,
    language: str = "en",
    notes: str = None,
    card_name: str = None,
    set_name: str = None,
    image_url: str = None
):
    """
    Adds or updates a card entry in user_cards with denormalized metadata.
    """
    existing_entry = supabase.table("user_cards") \
        .select("id, quantity") \
        .eq("user_id", user_id) \
        .eq("scryfall_id", scryfall_id) \
        .eq("finish", finish) \
        .eq("condition", condition) \
        .execute()

    if existing_entry.data:
        card_record = existing_entry.data[0]
        new_quantity = card_record["quantity"] + quantity
        
        response = supabase.table("user_cards") \
            .update({"quantity": new_quantity}) \
            .eq("id", card_record["id"]) \
            .execute()
    else:
        data = {
            "user_id": user_id,
            "scryfall_id": scryfall_id,
            "finish": finish,
            "condition": condition,
            "language": language,
            "quantity": quantity,
            "purchase_price": purchase_price,
            "notes": notes,
            "card_name": card_name,
            "set_name": set_name,
            "image_url": image_url
        }
        response = supabase.table("user_cards").insert(data).execute()

    return response.data[0] if response.data else None


def get_user_library(user_id: str):
    """Fetches all items in user_cards for a given user UUID."""
    response = supabase.table("user_cards").select("*").eq("user_id", user_id).execute()
    return response.data if response.data else []

def update_library_card(entry_id: str, quantity: int = None, condition: str = None):
    """Updates quantity and/or condition for a specific card entry in user_cards."""
    update_data = {}
    if quantity is not None:
        update_data["quantity"] = quantity
    if condition is not None:
        update_data["condition"] = condition

    if not update_data:
        return None

    response = supabase.table("user_cards") \
        .update(update_data) \
        .eq("id", entry_id) \
        .execute()
    
    return response.data[0] if response.data else None


def remove_from_library(entry_id: str):
    """Deletes a card entry from user_cards by its row ID."""
    response = supabase.table("user_cards") \
        .delete() \
        .eq("id", entry_id) \
        .execute()
    
    return response.data


# ==========================================
# Wishlist Functions
# ==========================================

def add_to_wishlist(
    user_id: str, 
    scryfall_id: str, 
    card_name: str = None, 
    set_name: str = None, 
    image_url: str = None
) -> bool:
    """Adds a card with metadata to the user's wishlist in Supabase."""
    try:
        data = {
            "user_id": user_id,
            "scryfall_id": scryfall_id,
            "card_name": card_name,
            "set_name": set_name,
            "image_url": image_url
        }
        response = supabase.table("wishlists").insert(data).execute()
        return bool(response.data)
    except Exception:
        return False


def remove_from_wishlist(user_id: str, scryfall_id: str) -> None:
    """Removes a card from the user's wishlist in Supabase."""
    supabase.table("wishlists") \
        .delete() \
        .eq("user_id", user_id) \
        .eq("scryfall_id", scryfall_id) \
        .execute()


def get_user_wishlist(user_id: str) -> list[dict]:
    """Returns all rows in the user's wishlist."""
    response = supabase.table("wishlists") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()
    
    return response.data if response.data else []

# ==========================================
# Card Tagging Functions
# ==========================================

def update_card_tags(entry_id: int, tags: list[str]):
    return supabase.table("user_cards").update({"tags": tags}).eq("id", entry_id).execute()