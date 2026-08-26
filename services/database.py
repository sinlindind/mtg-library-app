import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def init_supabase() -> Client:
    url: str = st.secrets["supabase"]["url"]
    key: str = st.secrets["supabase"]["key"]
    return create_client(url, key)


supabase = init_supabase()

# ==========================================
# User Functions
# ==========================================


def create_user(
    username: str,
    email: str,
    password_hash: str,
    salt: str,
    verification_token: str = None,
):
    data = {
        "username": username,
        "email": email,
        "password_hash": f"{password_hash}:{salt}",
        "verification_token": verification_token,
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
    response = (
        supabase.table("users")
        .update({"is_verified": True})
        .eq("email", email)
        .execute()
    )
    return response.data[0] if response.data else None


# ==========================================
# User Cards Functions (Simplified)
# ==========================================


def add_card_to_library(
    user_id: str,
    scryfall_id: str,
    quantity: int = 1,
    card_name: str = None,
    set_name: str = None,
    image_url: str = None,
):
    existing_entry = (
        supabase.table("user_cards")
        .select("id, quantity")
        .eq("user_id", user_id)
        .eq("scryfall_id", scryfall_id)
        .execute()
    )

    if existing_entry.data:
        card_record = existing_entry.data[0]
        new_quantity = card_record["quantity"] + quantity

        response = (
            supabase.table("user_cards")
            .update({"quantity": new_quantity})
            .eq("id", card_record["id"])
            .execute()
        )
    else:
        data = {
            "user_id": user_id,
            "scryfall_id": scryfall_id,
            "quantity": quantity,
            "card_name": card_name,
            "set_name": set_name,
            "image_url": image_url,
        }
        response = supabase.table("user_cards").insert(data).execute()

    return response.data[0] if response.data else None


def get_user_library(user_id: str):
    response = supabase.table("user_cards").select("*").eq("user_id", user_id).execute()
    return response.data if response.data else []


def update_library_card(entry_id: str, quantity: int = None):
    if quantity is None:
        return None

    response = (
        supabase.table("user_cards")
        .update({"quantity": quantity})
        .eq("id", entry_id)
        .execute()
    )

    return response.data[0] if response.data else None


def remove_from_library(entry_id: str):
    response = supabase.table("user_cards").delete().eq("id", entry_id).execute()
    return response.data


# ==========================================
# Wishlist Functions (Simplified)
# ==========================================


def add_to_wishlist(
    user_id: str,
    scryfall_id: str,
    card_name: str = None,
    set_name: str = None,
    image_url: str = None,
) -> bool:
    try:
        data = {
            "user_id": user_id,
            "scryfall_id": scryfall_id,
            "card_name": card_name,
            "set_name": set_name,
            "image_url": image_url,
        }
        response = supabase.table("wishlists").insert(data).execute()
        return bool(response.data)
    except Exception:
        return False


def remove_from_wishlist(user_id: str, scryfall_id: str) -> None:
    (
        supabase.table("wishlists")
        .delete()
        .eq("user_id", user_id)
        .eq("scryfall_id", scryfall_id)
        .execute()
    )


def get_user_wishlist(user_id: str) -> list[dict]:
    response = (
        supabase.table("wishlists")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return response.data if response.data else []


# ==========================================
# Card Tagging Functions
# ==========================================


def update_card_tags(entry_id: int, tags: list[str]):
    return (
        supabase.table("user_cards")
        .update({"tags": tags})
        .eq("id", entry_id)
        .execute()
    )


# ==========================================
# Pagination Functions (Name Sorting Only)
# ==========================================


def get_user_library_paginated(
    user_id,
    limit=25,
    offset=0,
    search_query=None,
    sort_by="Name (A-Z)",
):
    query = (
        supabase.table("user_cards")
        .select("*", count="exact")
        .eq("user_id", user_id)
        .gt("quantity", 0)
    )

    if search_query:
        query = query.or_(
            f"card_name.ilike.%{search_query}%,set_name.ilike.%{search_query}%"
        )

    if sort_by == "Name (Z-A)":
        query = query.order("card_name", desc=True)
    else:
        query = query.order("card_name", desc=False)

    response = query.range(offset, offset + limit - 1).execute()
    rows = response.data if response.data else []
    total_count = response.count if response.count is not None else len(rows)

    return rows, total_count


def get_user_wishlist_paginated(
    user_id,
    limit=25,
    offset=0,
    search_query=None,
    sort_by="Name (A-Z)",
):
    query = (
        supabase.table("wishlists")
        .select("*", count="exact")
        .eq("user_id", user_id)
    )

    if search_query:
        query = query.or_(
            f"card_name.ilike.%{search_query}%,set_name.ilike.%{search_query}%"
        )

    if sort_by == "Name (Z-A)":
        query = query.order("card_name", desc=True)
    else:
        query = query.order("card_name", desc=False)

    response = query.range(offset, offset + limit - 1).execute()
    items = response.data if response.data else []
    total_count = response.count if response.count is not None else len(items)

    return items, total_count