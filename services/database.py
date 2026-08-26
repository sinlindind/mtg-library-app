import streamlit as st
from supabase import create_client, Client

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
    data = {
        "username": username,
        "email": email,
        "password_hash": f"{password_hash}:{salt}",
        "verification_token": verification_token
    }
    response = supabase.table("users").insert(data).execute()
    return response.data[0] if response.data else None


def get_user_by_username(username: str):
    response = supabase.table("users").select("*").eq("username", username).execute()
    return response.data[0] if response.data else None


def get_user_by_email(email: str):
    response = supabase.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None


def verify_user_email(email: str):
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
    response = supabase.table("user_cards").select("*").eq("user_id", user_id).execute()
    return response.data if response.data else []


def update_library_card(entry_id: str, quantity: int = None, condition: str = None):
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
    response = supabase.table("user_cards") \
        .delete() \
        .eq("id", entry_id) \
        .execute()
    
    return response.data


def update_user_card_metadata(entry_id: int, card_name: str, set_name: str, image_url: str):
    return supabase.table("user_cards").update({
        "card_name": card_name,
        "set_name": set_name,
        "image_url": image_url
    }).eq("id", entry_id).execute()


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
    supabase.table("wishlists") \
        .delete() \
        .eq("user_id", user_id) \
        .eq("scryfall_id", scryfall_id) \
        .execute()


def get_user_wishlist(user_id: str) -> list[dict]:
    response = supabase.table("wishlists") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()
    
    return response.data if response.data else []


def update_wishlist_metadata(wishlist_id: str, card_name: str, set_name: str, image_url: str):
    return supabase.table("wishlists").update({
        "card_name": card_name,
        "set_name": set_name,
        "image_url": image_url
    }).eq("id", wishlist_id).execute()


# ==========================================
# Card Tagging Functions
# ==========================================

def update_card_tags(entry_id: int, tags: list[str]):
    return supabase.table("user_cards").update({"tags": tags}).eq("id", entry_id).execute()


# ==========================================
# Pagination & Standardized Sorting Functions
# ==========================================

def get_user_library_paginated(user_id, limit=25, offset=0, search_query=None, sort_by="Name (A-Z)", fetch_cached_card_fn=None):
    """Fetch paginated library items aggregated by scryfall_id with full standardized sorting."""
    query = supabase.table("user_cards").select("*").eq("user_id", user_id).gt("quantity", 0)

    if search_query:
        query = query.or_(f"card_name.ilike.%{search_query}%,set_name.ilike.%{search_query}%")

    response = query.execute()
    all_rows = response.data if response.data else []

    grouped_cards = {}
    for row in all_rows:
        sid = row["scryfall_id"]
        if sid not in grouped_cards:
            grouped_cards[sid] = {
                "scryfall_id": sid,
                "total_quantity": 0,
                "entries": []
            }
        grouped_cards[sid]["entries"].append(row)
        grouped_cards[sid]["total_quantity"] += row.get("quantity", 1)

    group_list = list(grouped_cards.values())

    # Helper function for fetching card details when sorting by Price or Release Date
    def _get_card_details(scryfall_id):
        if fetch_cached_card_fn:
            return fetch_cached_card_fn(scryfall_id) or {}
        return {}

    # Apply Standardized Sorting Logic
    if sort_by == "Name (A-Z)":
        group_list.sort(key=lambda x: (x["entries"][0].get("card_name") or "").lower())
    elif sort_by == "Name (Z-A)":
        group_list.sort(key=lambda x: (x["entries"][0].get("card_name") or "").lower(), reverse=True)
    elif sort_by == "Price: Low to High":
        def get_price(x):
            c = _get_card_details(x["scryfall_id"])
            val = c.get("prices", {}).get("usd")
            try:
                return float(val) if val else 0.0
            except (ValueError, TypeError):
                return 0.0
        group_list.sort(key=get_price)
    elif sort_by == "Price: High to Low":
        def get_price(x):
            c = _get_card_details(x["scryfall_id"])
            val = c.get("prices", {}).get("usd")
            try:
                return float(val) if val else 0.0
            except (ValueError, TypeError):
                return 0.0
        group_list.sort(key=get_price, reverse=True)
    elif sort_by == "Released: Newest":
        group_list.sort(
            key=lambda x: _get_card_details(x["scryfall_id"]).get("released_at", ""),
            reverse=True
        )
    elif sort_by == "Released: Oldest":
        group_list.sort(
            key=lambda x: _get_card_details(x["scryfall_id"]).get("released_at", "")
        )

    total_count = len(group_list)
    paged_groups = group_list[offset:offset + limit]

    return paged_groups, total_count


def get_user_wishlist_paginated(user_id, limit=25, offset=0, search_query=None, sort_by="Name (A-Z)", fetch_cached_card_fn=None):
    """Fetch paginated wishlist items with full standardized sorting."""
    query = supabase.table("wishlists").select("*", count="exact").eq("user_id", user_id)

    if search_query:
        query = query.or_(f"card_name.ilike.%{search_query}%,set_name.ilike.%{search_query}%")

    response = query.execute()
    items = response.data if response.data else []

    # Helper function for fetching card details when sorting by Price or Release Date
    def _get_card_details(scryfall_id):
        if fetch_cached_card_fn:
            return fetch_cached_card_fn(scryfall_id) or {}
        return {}

    # Apply Standardized Sorting Logic
    if sort_by == "Name (A-Z)":
        items.sort(key=lambda x: (x.get("card_name") or "").lower())
    elif sort_by == "Name (Z-A)":
        items.sort(key=lambda x: (x.get("card_name") or "").lower(), reverse=True)
    elif sort_by == "Price: Low to High":
        def get_price(x):
            c = _get_card_details(x.get("scryfall_id"))
            val = c.get("prices", {}).get("usd")
            try:
                return float(val) if val else 0.0
            except (ValueError, TypeError):
                return 0.0
        items.sort(key=get_price)
    elif sort_by == "Price: High to Low":
        def get_price(x):
            c = _get_card_details(x.get("scryfall_id"))
            val = c.get("prices", {}).get("usd")
            try:
                return float(val) if val else 0.0
            except (ValueError, TypeError):
                return 0.0
        items.sort(key=get_price, reverse=True)
    elif sort_by == "Released: Newest":
        items.sort(
            key=lambda x: _get_card_details(x.get("scryfall_id")).get("released_at", ""),
            reverse=True
        )
    elif sort_by == "Released: Oldest":
        items.sort(
            key=lambda x: _get_card_details(x.get("scryfall_id")).get("released_at", "")
        )

    total_count = len(items)
    paged_items = items[offset:offset + limit]

    return paged_items, total_count