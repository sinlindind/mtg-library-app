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
    image_url: str = None,
    current_price: float = None,
    released_at: str = None,
):
  existing_entry = (
      supabase.table("user_cards")
      .select("id, quantity")
      .eq("user_id", user_id)
      .eq("scryfall_id", scryfall_id)
      .eq("finish", finish)
      .eq("condition", condition)
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
        "finish": finish,
        "condition": condition,
        "language": language,
        "quantity": quantity,
        "purchase_price": purchase_price,
        "notes": notes,
        "card_name": card_name,
        "set_name": set_name,
        "image_url": image_url,
        "current_price": current_price,
        "released_at": released_at,
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

  response = (
      supabase.table("user_cards")
      .update(update_data)
      .eq("id", entry_id)
      .execute()
  )

  return response.data[0] if response.data else None


def remove_from_library(entry_id: str):
  response = supabase.table("user_cards").delete().eq("id", entry_id).execute()

  return response.data


def update_user_card_metadata(
    entry_id: int,
    card_name: str,
    set_name: str,
    image_url: str,
    current_price: float = None,
    released_at: str = None,
):
  update_data = {
      "card_name": card_name,
      "set_name": set_name,
      "image_url": image_url,
  }
  if current_price is not None:
    update_data["current_price"] = current_price
  if released_at is not None:
    update_data["released_at"] = released_at

  return (
      supabase.table("user_cards")
      .update(update_data)
      .eq("id", entry_id)
      .execute()
  )


# ==========================================
# Wishlist Functions
# ==========================================


def add_to_wishlist(
    user_id: str,
    scryfall_id: str,
    card_name: str = None,
    set_name: str = None,
    image_url: str = None,
    current_price: float = None,
    released_at: str = None,
) -> bool:
  try:
    data = {
        "user_id": user_id,
        "scryfall_id": scryfall_id,
        "card_name": card_name,
        "set_name": set_name,
        "image_url": image_url,
        "current_price": current_price,
        "released_at": released_at,
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


def update_wishlist_metadata(
    wishlist_id: str,
    card_name: str,
    set_name: str,
    image_url: str,
    current_price: float = None,
    released_at: str = None,
):
  update_data = {
      "card_name": card_name,
      "set_name": set_name,
      "image_url": image_url,
  }
  if current_price is not None:
    update_data["current_price"] = current_price
  if released_at is not None:
    update_data["released_at"] = released_at

  return (
      supabase.table("wishlists")
      .update(update_data)
      .eq("id", wishlist_id)
      .execute()
  )


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
# Pagination & Database-Level Sorting Functions
# ==========================================


def get_user_library_paginated(
    user_id,
    limit=25,
    offset=0,
    search_query=None,
    sort_by="Name (A-Z)",
    fetch_cached_card_fn=None,
):
  """Fetch paginated library items with SQL-level/aggregated sorting and pagination."""
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

  # Standard DB-level sorting mapping
  if sort_by == "Name (A-Z)":
    query = query.order("card_name", desc=False)
  elif sort_by == "Name (Z-A)":
    query = query.order("card_name", desc=True)
  elif sort_by == "Released: Newest":
    query = query.order("released_at", desc=True)
  elif sort_by == "Released: Oldest":
    query = query.order("released_at", desc=False)
  elif sort_by == "Price: Low to High":
    query = query.order("current_price", desc=False)
  elif sort_by == "Price: High to Low":
    query = query.order("current_price", desc=True)

  response = query.range(offset, offset + limit - 1).execute()
  rows = response.data if response.data else []
  total_count = response.count if response.count is not None else len(rows)

  # Group the slice and calculate aggregate properties (max unit price & total group value)
  grouped_cards = {}
  for row in rows:
    sid = row["scryfall_id"]
    if sid not in grouped_cards:
      grouped_cards[sid] = {
          "scryfall_id": sid,
          "total_quantity": 0,
          "entries": [],
          "max_unit_price": 0.0,
          "total_group_value": 0.0,
      }
    grouped_cards[sid]["entries"].append(row)
    qty = row.get("quantity", 1)
    grouped_cards[sid]["total_quantity"] += qty

    price = row.get("current_price") or 0.0
    if price > grouped_cards[sid]["max_unit_price"]:
      grouped_cards[sid]["max_unit_price"] = price
    grouped_cards[sid]["total_group_value"] += price * qty

  result_list = list(grouped_cards.values())

  # Post-grouping sort option handling for highest/lowest total value or max price per row
  if sort_by == "Price: High to Low":
    result_list = sorted(
        result_list, key=lambda x: x["total_group_value"], reverse=True
    )
  elif sort_by == "Price: Low to High":
    result_list = sorted(result_list, key=lambda x: x["total_group_value"])

  return result_list, total_count


def get_user_wishlist_paginated(
    user_id,
    limit=25,
    offset=0,
    search_query=None,
    sort_by="Name (A-Z)",
    fetch_cached_card_fn=None,
):
  """Fetch paginated wishlist items with SQL-level sorting and pagination."""
  query = (
      supabase.table("wishlists")
      .select("*", count="exact")
      .eq("user_id", user_id)
  )

  if search_query:
    query = query.or_(
        f"card_name.ilike.%{search_query}%,set_name.ilike.%{search_query}%"
    )

  if sort_by == "Name (A-Z)":
    query = query.order("card_name", desc=False)
  elif sort_by == "Name (Z-A)":
    query = query.order("card_name", desc=True)
  elif sort_by == "Price: Low to High":
    query = query.order("current_price", desc=False)
  elif sort_by == "Price: High to Low":
    query = query.order("current_price", desc=True)
  elif sort_by == "Released: Newest":
    query = query.order("released_at", desc=True)
  elif sort_by == "Released: Oldest":
    query = query.order("released_at", desc=False)

  response = query.range(offset, offset + limit - 1).execute()
  items = response.data if response.data else []
  total_count = response.count if response.count is not None else len(items)

  return items, total_count


def sync_user_prices_on_login(user_id: str, fetch_cached_card_fn):
  """Sync fresh Scryfall prices to library and wishlist entries upon login."""
  lib_response = (
      supabase.table("user_cards")
      .select("id, scryfall_id, finish")
      .eq("user_id", user_id)
      .execute()
  )
  if lib_response.data:
    for row in lib_response.data:
      card_data = fetch_cached_card_fn(row["scryfall_id"])
      if card_data:
        finish = row.get("finish", "nonfoil")
        price_key = "usd_foil" if finish == "foil" else "usd"
        raw_price = card_data.get("prices", {}).get(price_key)
        try:
          price_val = float(raw_price) if raw_price else 0.0
        except (ValueError, TypeError):
          price_val = 0.0

        update_user_card_metadata(
            entry_id=row["id"],
            card_name=card_data.get("name"),
            set_name=card_data.get("set_name"),
            image_url=card_data.get("image_uris", {}).get("large", ""),
            current_price=price_val,
            released_at=card_data.get("released_at"),
        )

  wish_response = (
      supabase.table("wishlists")
      .select("id, scryfall_id")
      .eq("user_id", user_id)
      .execute()
  )
  if wish_response.data:
    for row in wish_response.data:
      card_data = fetch_cached_card_fn(row["scryfall_id"])
      if card_data:
        raw_price = card_data.get("prices", {}).get("usd")
        try:
          price_val = float(raw_price) if raw_price else 0.0
        except (ValueError, TypeError):
          price_val = 0.0

        update_wishlist_metadata(
            wishlist_id=row["id"],
            card_name=card_data.get("name"),
            set_name=card_data.get("set_name"),
            image_url=card_data.get("image_uris", {}).get("large", ""),
            current_price=price_val,
            released_at=card_data.get("released_at"),
        )