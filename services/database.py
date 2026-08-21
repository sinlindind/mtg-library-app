import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def init_supabase() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

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
    notes: str = None
):
    """
    Adds or updates a card entry in user_cards.
    If an entry matching (user_id, scryfall_id, finish, condition) exists, 
    it increments the existing quantity.
    """
    # 1. Check if card entry already exists
    existing_entry = supabase.table("user_cards") \
        .select("id, quantity") \
        .eq("user_id", user_id) \
        .eq("scryfall_id", scryfall_id) \
        .eq("finish", finish) \
        .eq("condition", condition) \
        .execute()

    if existing_entry.data:
        # 2a. Update quantity if entry already exists
        card_record = existing_entry.data[0]
        new_quantity = card_record["quantity"] + quantity
        
        response = supabase.table("user_cards") \
            .update({"quantity": new_quantity}) \
            .eq("id", card_record["id"]) \
            .execute()
    else:
        # 2b. Insert new card record
        data = {
            "user_id": user_id,
            "scryfall_id": scryfall_id,
            "finish": finish,
            "condition": condition,
            "language": language,
            "quantity": quantity,
            "purchase_price": purchase_price,
            "notes": notes
        }
        response = supabase.table("user_cards").insert(data).execute()

    return response.data[0] if response.data else None


def get_user_library(user_id: str):
    """Fetches all cards in user_cards for a specific user UUID."""
    response = supabase.table("user_cards").select("*").eq("user_id", user_id).execute()
    return response.data if response.data else []