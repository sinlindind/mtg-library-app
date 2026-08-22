import streamlit as st
from streamlit_searchbox import st_searchbox
import requests
import time

# --- CONFIG & PAGE SETUP ---
st.set_page_config(page_title="MTG Card Manager", page_icon="🃏", layout="wide")

# --- MOCK / BACKEND FUNCTIONS ---
def get_user_library(user_id):
    """Retrieve user's stored library from session state."""
    if "user_library" not in st.session_state:
        st.session_state.user_library = []
    return st.session_state.user_library

def add_card_to_library(user_id, scryfall_id, finish, quantity, condition, purchase_price):
    """Add or update a card in the user's local session library."""
    library = get_user_library(user_id)
    # Check if entry already exists
    for item in library:
        if item["scryfall_id"] == scryfall_id and item["finish"] == finish and item["condition"] == condition:
            item["quantity"] += quantity
            return
    
    # Otherwise add new item
    library.append({
        "scryfall_id": scryfall_id,
        "finish": finish,
        "quantity": quantity,
        "condition": condition,
        "purchase_price": purchase_price
    })

def search_scryfall_names(searchterm: str):
    """Autocomplete function for streamlit-searchbox using Scryfall API."""
    if not searchterm or len(searchterm.strip()) < 2:
        return []
    try:
        url = f"https://api.scryfall.com/cards/autocomplete?q={searchterm}"
        res = requests.get(url, timeout=5).json()
        return res.get("data", [])
    except Exception:
        return []

def search_cards(card_name: str):
    """Fetch card printings from Scryfall by exact/fuzzy name."""
    try:
        url = f"https://api.scryfall.com/cards/search?q=exact%3A%22{card_name}%22+unique%3Aprints"
        res = requests.get(url, timeout=5).json()
        if res.get("object") == "list":
            return res.get("data", [])
        
        # Fallback to search query if exact match yields no list
        url = f"https://api.scryfall.com/cards/search?q={card_name}"
        res = requests.get(url, timeout=5).json()
        return res.get("data", [])
    except Exception:
        return []

def get_card_image_url(card, size="large"):
    """Helper to extract card image URL safely across multi-face cards."""
    if "image_uris" in card:
        return card["image_uris"].get(size, "")
    elif "card_faces" in card and len(card["card_faces"]) > 0:
        return card["card_faces"][0].get("image_uris", {}).get(size, "")
    return "https://via.placeholder.com/300x418?text=No+Image"


# --- MAIN APPLICATION ---
def main():
    # Mock current user context
    user = {"id": "user_123", "name": "MTG Collector"}

    st.sidebar.title("Navigation")
    menu_selection = st.sidebar.radio("Go to", ["Search", "My Library"])

    # --- SCREEN 1: SEARCH ---
    if menu_selection == "Search":
        st.title("🔍 MTG Card Search")
        
        user_library = get_user_library(user["id"])
        
        # Initialize explicit persistent state for query and active search results
        if "active_search_query" not in st.session_state:
            st.session_state.active_search_query = ""
        if "active_search_results" not in st.session_state:
            st.session_state.active_search_results = []

        col_search, col_clear = st.columns([5, 1])

        with col_search:
            # Native autocomplete searchbox
            selected_card = st_searchbox(
                search_scryfall_names,
                placeholder="Type a card name (e.g. 'Sol Ring')...",
                key="scryfall_autocomplete_box"
            )

        with col_clear:
            # Custom clear button that explicitly resets persistent search state
            if st.button("🗑️ Clear", key="clear_search_btn", use_container_width=True):
                st.session_state.active_search_query = ""
                st.session_state.active_search_results = []
                st.rerun()

        # Update cache ONLY when a valid selection is made
        if selected_card and len(selected_card.strip()) >= 2:
            query = selected_card.strip()
            if query != st.session_state.active_search_query:
                with st.spinner(f"Searching printings for '{query}'..."):
                    results = search_cards(query)
                    st.session_state.active_search_query = query
                    st.session_state.active_search_results = results

        # Always render cached results if present
        results = st.session_state.active_search_results
        active_query = st.session_state.active_search_query

        if active_query:
            if not results:
                st.warning(f"No cards found matching '{active_query}'.")
            else:
                st.success(f"Found **{len(results)}** printings for **{active_query}**")
                
                for idx, card in enumerate(results):
                    card_id = f"{card['id']}_{idx}"
                    owned_entries = [item for item in user_library if item.get("scryfall_id") == card["id"]]
                    
                    col_img, col_info, col_actions = st.columns([1.5, 2.5, 2])
                    
                    with col_img:
                        img_url = get_card_image_url(card, size="large")
                        st.image(img_url, use_container_width=True)
                    
                    with col_info:
                        st.subheader(card.get("name", "Unknown Card"))
                        set_name = card.get("set_name", "Unknown Set")
                        set_code = card.get("set", "").upper()
                        st.markdown(f"**Set:** {set_name} (`{set_code}`)")
                        
                        prices = card.get("prices", {})
                        usd = prices.get("usd")
                        usd_foil = prices.get("usd_foil")
                        
                        st.markdown(f"**Regular Price:** ${usd if usd else 'N/A'}")
                        st.markdown(f"**Foil Price:** ${usd_foil if usd_foil else 'N/A'}")
                        
                        valid_owned = [item for item in owned_entries if item.get("quantity", 0) > 0]
                        if valid_owned:
                            st.markdown("---")
                            st.markdown("**In Library:**")
                            for item in valid_owned:
                                qty = item.get("quantity")
                                finish = item.get("finish", "nonfoil").capitalize()
                                cond = item.get("condition", "Near Mint")
                                st.markdown(f"• **{qty}x** {finish} ({cond})")
                    
                    with col_actions:
                        st.write("**Quick Add (Near Mint)**")
                        c_reg, c_foil = st.columns(2)
                        
                        with c_reg:
                            if st.button("➕ 1x Regular", key=f"qadd_reg_{card_id}", use_container_width=True):
                                add_card_to_library(
                                    user_id=user["id"],
                                    scryfall_id=card["id"],
                                    finish="nonfoil",
                                    quantity=1,
                                    condition="Near Mint",
                                    purchase_price=float(usd) if usd else None
                                )
                                st.toast("Added 1x Regular (Near Mint)!", icon="✅")
                                st.rerun()

                        with c_foil:
                            if st.button("✨ 1x Foil", key=f"qadd_foil_{card_id}", use_container_width=True):
                                add_card_to_library(
                                    user_id=user["id"],
                                    scryfall_id=card["id"],
                                    finish="foil",
                                    quantity=1,
                                    condition="Near Mint",
                                    purchase_price=float(usd_foil) if usd_foil else None
                                )
                                st.toast("Added 1x Foil (Near Mint)!", icon="✅")
                                st.rerun()

                        with st.popover("⚙️ Custom Add...", use_container_width=True):
                            st.caption("Add specific quantities or conditions")
                            custom_finish = st.selectbox("Finish", ["nonfoil", "foil"], key=f"c_fin_{card_id}")
                            custom_qty = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"c_qty_{card_id}")
                            custom_cond = st.selectbox(
                                "Condition", 
                                ["Near Mint", "Lightly Played", "Moderately Played", "Heavily Played", "Damaged"],
                                key=f"c_cond_{card_id}"
                            )
                            
                            if st.button("Add Custom Entry", key=f"c_btn_{card_id}", use_container_width=True):
                                price_val = usd_foil if custom_finish == "foil" else usd
                                add_card_to_library(
                                    user_id=user["id"],
                                    scryfall_id=card["id"],
                                    finish=custom_finish,
                                    quantity=custom_qty,
                                    condition=custom_cond,
                                    purchase_price=float(price_val) if price_val else None
                                )
                                st.toast(f"Added {custom_qty}x {custom_finish.capitalize()}!", icon="✅")
                                st.rerun()

                    st.divider()

    # --- SCREEN 2: MY LIBRARY ---
    elif menu_selection == "My Library":
        st.title("📚 My Library")
        library = get_user_library(user["id"])
        
        if not library:
            st.info("Your library is empty. Use the Search tab to add cards!")
        else:
            st.write(f"Total Unique Entries: **{len(library)}**")
            for idx, entry in enumerate(library):
                st.write(f"**Card ID:** `{entry['scryfall_id']}` | **Qty:** {entry['quantity']} | **Finish:** {entry['finish']} | **Condition:** {entry['condition']}")

if __name__ == "__main__":
    main()