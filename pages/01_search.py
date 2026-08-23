import streamlit as st
import requests
from streamlit_searchbox import st_searchbox

from services.database import add_card_to_library, get_user_library, add_to_wishlist, remove_from_wishlist, get_user_wishlist
from services.scryfall import search_cards, get_card_image_url

# Guard route for unauthenticated users
if "user" not in st.session_state or st.session_state.user is None:
    st.switch_page("app.py")

user = st.session_state.user
user_library = get_user_library(user["id"])
user_wishlist = get_user_wishlist(user["id"])

# Helper function for autocomplete
def search_scryfall_names(search_term: str) -> list[str]:
    if not search_term or len(search_term.strip()) < 2:
        return []
    try:
        url = "https://api.scryfall.com/cards/autocomplete"
        headers = {"User-Agent": "MTGLibraryApp/1.0", "Accept": "application/json"}
        res = requests.get(url, params={"q": search_term}, headers=headers, timeout=3)
        if res.status_code == 200:
            return res.json().get("data", [])
    except Exception:
        pass
    return []

# Helper function for parsing prices cleanly
def parse_price(c):
    prices = c.get("prices", {}) if isinstance(c, dict) else {}
    p = prices.get("usd") or prices.get("usd_foil") or "0"
    try:
        return float(p)
    except (ValueError, TypeError):
        return 0.0

# Sidebar setup
with st.sidebar:
    st.title(f"👤 {user['username']}")
    st.markdown("### 🔍 Card Search")
    
    if "searchbox_key_counter" not in st.session_state:
        st.session_state.searchbox_key_counter = 0
    if "active_search_label" not in st.session_state:
        st.session_state.active_search_label = ""
    if "active_search_results" not in st.session_state:
        st.session_state.active_search_results = []

    current_search_key = f"scryfall_box_{st.session_state.searchbox_key_counter}"
    search_selection = st_searchbox(
        search_scryfall_names,
        placeholder="Type card name...",
        key=current_search_key
    )

    if search_selection and len(search_selection.strip()) >= 2:
        query = search_selection.strip()
        if query != st.session_state.active_search_label:
            with st.spinner("Fetching printings..."):
                results = search_cards(query)
                st.session_state.active_search_label = query
                st.session_state.active_search_results = results
                st.session_state.searchbox_key_counter += 1
                # Force navigation back to page top on fresh search
                st.switch_page("pages/01_search.py.py")

    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.switch_page("app.py")

# Main Content
if "active_sort_option" not in st.session_state:
    st.session_state.active_sort_option = "Release Date (Newest First)"

if not st.session_state.active_search_label:
    st.info("👈 Use the search bar in the sidebar to find Magic cards.")
else:
    results = st.session_state.active_search_results
    
    if not results:
        st.warning(f"No cards found matching '{st.session_state.active_search_label}'.")
    else:
        col_info, col_sort = st.columns([3, 1], vertical_alignment="center")
        
        with col_info:
            st.subheader(f"🔍 **{st.session_state.active_search_label}** ({len(results)} printings)")

        def on_sort_change():
            st.session_state.active_sort_option = st.session_state.search_sort_dropdown

        with col_sort:
            sort_options = [
                "Release Date (Newest First)",
                "Release Date (Oldest First)",
                "Price: High to Low",
                "Price: Low to High",
                "Name (A-Z)"
            ]
            current_idx = sort_options.index(st.session_state.active_sort_option) if st.session_state.active_sort_option in sort_options else 0
            
            sort_option = st.selectbox(
                "Sort results by",
                options=sort_options,
                index=current_idx,
                key="search_sort_dropdown",
                on_change=on_sort_change,
                label_visibility="collapsed"
            )

        sorted_results = list(results)
        if sort_option == "Release Date (Newest First)":
            sorted_results.sort(key=lambda x: x.get("released_at", ""), reverse=True)
        elif sort_option == "Release Date (Oldest First)":
            sorted_results.sort(key=lambda x: x.get("released_at", ""))
        elif sort_option == "Price: High to Low":
            sorted_results.sort(key=parse_price, reverse=True)
        elif sort_option == "Price: Low to High":
            sorted_results.sort(key=parse_price)
        elif sort_option == "Name (A-Z)":
            sorted_results.sort(key=lambda x: x.get("name", "").lower())

        cols = st.columns(3)
        for idx, card in enumerate(sorted_results):
            col = cols[idx % 3]
            card_id = f"{card['id']}_{idx}"
            owned_entries = [item for item in user_library if item.get("scryfall_id") == card["id"]]
            is_in_wishlist = card["id"] in user_wishlist
            tcg_url = card.get("purchase_uris", {}).get("tcgplayer")
            
            with col:
                with st.container(border=True):
                    img_url = get_card_image_url(card, size="large")
                    st.image(img_url, use_container_width=True)
                    
                    if tcg_url:
                        st.markdown(f"**{card.get('name', 'Unknown')}** ([TCG]({tcg_url}))")
                    else:
                        st.markdown(f"**{card.get('name', 'Unknown')}**")
                    valid_owned = [item for item in owned_entries if item.get("quantity", 0) > 0]
                    total_qty = sum(item.get("quantity", 0) for item in valid_owned)
                    if total_qty > 0:
                        st.caption(f"✅ **{total_qty}** in library")
                    else:
                        st.caption(f"{total_qty} owned")
                    set_name = card.get("set_name", "Unknown Set")
                    released_date = card.get("released_at", "")
                    st.caption(f"{set_name}")
                    st.caption(f"{released_date}")
                    
                    prices = card.get("prices", {})
                    usd = prices.get("usd")
                    usd_foil = prices.get("usd_foil")
                    st.caption(f"Reg: **\\${usd if usd else 'N/A'}** | Foil: **\\${usd_foil if usd_foil else 'N/A'}**")

                    available_finishes = card.get("finishes", ["nonfoil", "foil"])
                    has_nonfoil = "nonfoil" in available_finishes
                    has_foil = "foil" in available_finishes or "etched" in available_finishes

                    c1, c2 = st.columns(2)
                    if has_nonfoil and has_foil:
                        with c1:
                            if st.button("➕ 1x Reg", key=f"qadd_reg_{card_id}", use_container_width=True):
                                add_card_to_library(user["id"], card["id"], "nonfoil", 1, "Near Mint", float(usd) if usd else None)
                                st.toast("Added 1x Regular!", icon="✅")
                                st.rerun()
                        with c2:
                            if st.button("✨ 1x Foil", key=f"qadd_foil_{card_id}", use_container_width=True):
                                add_card_to_library(user["id"], card["id"], "foil", 1, "Near Mint", float(usd_foil) if usd_foil else None)
                                st.toast("Added 1x Foil!", icon="✅")
                                st.rerun()
                    elif has_nonfoil:
                        with c1:
                            if st.button("➕ 1x Reg", key=f"qadd_reg_{card_id}", use_container_width=True):
                                add_card_to_library(user["id"], card["id"], "nonfoil", 1, "Near Mint", float(usd) if usd else None)
                                st.toast("Added 1x Regular!", icon="✅")
                                st.rerun()
                    elif has_foil:
                        with c1:
                            if st.button("✨ 1x Foil", key=f"qadd_foil_{card_id}", use_container_width=True):
                                add_card_to_library(user["id"], card["id"], "foil", 1, "Near Mint", float(usd_foil) if usd_foil else None)
                                st.toast("Added 1x Foil!", icon="✅")
                                st.rerun()

                    c_wish, c_tcg = st.columns(2)
                    with c_wish:
                        wishlist_state = st.checkbox("❤️ Wishlist", value=is_in_wishlist, key=f"wishlist_chk_{card_id}")
                        if wishlist_state != is_in_wishlist:
                            if wishlist_state:
                                add_to_wishlist(user["id"], card["id"])
                                st.toast("Added to Wishlist!", icon="❤️")
                            else:
                                remove_from_wishlist(user["id"], card["id"])
                                st.toast("Removed from Wishlist", icon="🗑️")
                            st.rerun()