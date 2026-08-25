import streamlit as st
import requests

from services.database import (
    get_user_by_username,
    get_user_library,
    get_user_wishlist,
    add_card_to_library,
    remove_from_library,
    update_library_card,
    add_to_wishlist,
    remove_from_wishlist
)
from services.scryfall import search_cards, get_card_by_id, get_card_image_url
from utils.auth import verify_password

st.set_page_config(page_title="MTG Hub", page_icon="🃏", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for compact layout, sticky actions, and zero clipping
st.markdown("""
    <style>
        /* 1. Hide Streamlit's native top header bar */
        header[data-testid="stHeader"] {
            display: none !important;
        }

        /* 2. Hide standard sidebar and toggle control completely */
        [data-testid="stSidebar"], 
        [data-testid="collapsedControl"] { 
            display: none !important; 
        }

        /* 3. Adjust top padding for main page container */
        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
        }

        /* 4. Prevent column containers from clipping top/bottom overflow */
        div[data-testid="column"] {
            overflow: visible !important;
        }

        /* 5. Sticky styling for text and action columns so icons stay visible during scrolling */
        div[data-testid="column"]:nth-of-type(2),
        div[data-testid="column"]:nth-of-type(3),
        div[data-testid="column"]:nth-of-type(4) {
            position: sticky !important;
            top: 1rem !important;
            align-self: flex-start !important;
        }

        /* 6. Standardize button heights and vertical alignment */
        div.stButton > button {
            height: 2.25rem !important;
            padding: 0 0.5rem !important;
            font-size: 0.85rem !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }

        /* 7. Standardize segmented control height */
        div[data-testid="stSegmentedControl"] {
            min-height: 2.25rem !important;
        }

        /* Compact row divider */
        .card-row {
            display: flex;
            align-items: flex-start;
            border-bottom: 1px solid #2e303e;
            padding: 0.8rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

# Initialize In-Memory Card Cache
if "card_cache" not in st.session_state:
    st.session_state.card_cache = {}

def fetch_cached_card(scryfall_id):
    """Retrieve card payload from session memory or query network once."""
    if scryfall_id not in st.session_state.card_cache:
        card = get_card_by_id(scryfall_id)
        if card:
            st.session_state.card_cache[scryfall_id] = card
    return st.session_state.card_cache.get(scryfall_id)

# --- UNAUTHENTICATED VIEW (LOGIN) ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🃏 MTG Library App")
        st.subheader("Login to your account")

        with st.form("login_form", clear_on_submit=False):
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            login_submitted = st.form_submit_button("Login", use_container_width=True)

        # Autofocus script: sets cursor directly into the username field on load
        st.components.v1.html("""
            <script>
                const inputs = window.parent.document.querySelectorAll('input[type="text"]');
                if (inputs.length > 0) {
                    inputs[0].focus();
                }
            </script>
        """, height=0)

        if login_submitted:
            user_record = get_user_by_username(login_username)
            if user_record:
                stored_hash, stored_salt = user_record["password_hash"].split(":")
                if verify_password(login_password, stored_hash, stored_salt):
                    st.session_state.user = user_record
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            else:
                st.error("Invalid username or password.")

# --- AUTHENTICATED VIEW (APP DASHBOARD) ---
else:
    user = st.session_state.user

    # Cache user data in session memory
    if "user_library" not in st.session_state:
        st.session_state.user_library = get_user_library(user["id"])
    if "user_wishlist" not in st.session_state:
        st.session_state.user_wishlist = get_user_wishlist(user["id"])

    # List of wishlist IDs for fast UI checking
    wishlist_ids = [w["scryfall_id"] for w in st.session_state.user_wishlist]

    # --- TOP NAVIGATION BAR ---
    col_brand, col_nav, col_user = st.columns([1.5, 3, 1.5], vertical_alignment="center")

    with col_brand:
        st.markdown("### 🃏 **MTG Hub**")

    with col_nav:
        current_tab = st.segmented_control(
            label="Navigation",
            options=["🔍 Search", "📚 Library", "❤️ Wishlist"],
            default="🔍 Search",
            label_visibility="collapsed"
        )

    with col_user:
        u_col, lg_col = st.columns([2, 1], vertical_alignment="center")
        u_col.caption(f"👤 **{user['username']}**")
        if lg_col.button("Logout", key="top_logout_btn"):
            st.session_state.clear()
            st.rerun()

    st.divider()

    # --- FRAGMENT: SEARCH ROW ---
    @st.fragment
    def render_search_row(card, idx):
        c_preview, c_info, c_price, c_actions = st.columns([1.8, 3.0, 1.5, 2.2])
        img_url = get_card_image_url(card, size="large") or get_card_image_url(card, size="normal")
        usd = card.get("prices", {}).get("usd") or "N/A"
        usd_foil = card.get("prices", {}).get("usd_foil") or "N/A"
        card_id = card["id"]
        c_name = card.get("name")
        s_name = card.get("set_name")

        # Cache search result
        st.session_state.card_cache[card_id] = card

        with c_preview:
            if img_url:
                st.image(img_url, use_container_width=True)

        with c_info:
            st.markdown(f"**{c_name}** · `{s_name}`")

        with c_price:
            st.caption(f"Reg: **${usd}** | Foil: **${usd_foil}**")

        with c_actions:
            b1, b2, b3 = st.columns(3)
            if b1.button("➕ Reg", key=f"add_reg_{card_id}_{idx}"):
                add_card_to_library(
                    user["id"], card_id, "nonfoil", 1, "Near Mint", 
                    float(usd) if usd != "N/A" else None, 
                    card_name=c_name, set_name=s_name, image_url=img_url
                )
                st.session_state.user_library = get_user_library(user["id"])
                st.toast(f"Added {c_name} (Reg)", icon="✅")

            if b2.button("✨ Foil", key=f"add_foil_{card_id}_{idx}"):
                add_card_to_library(
                    user["id"], card_id, "foil", 1, "Near Mint", 
                    float(usd_foil) if usd_foil != "N/A" else None,
                    card_name=c_name, set_name=s_name, image_url=img_url
                )
                st.session_state.user_library = get_user_library(user["id"])
                st.toast(f"Added {c_name} (Foil)", icon="✨")

            is_in_wishlist = card_id in wishlist_ids
            wish_label = "❤️" if is_in_wishlist else "🤍"
            if b3.button(wish_label, key=f"wish_{card_id}_{idx}"):
                if is_in_wishlist:
                    remove_from_wishlist(user["id"], card_id)
                    st.session_state.user_wishlist = get_user_wishlist(user["id"])
                    st.toast("Removed from Wishlist", icon="🗑️")
                else:
                    add_to_wishlist(user["id"], card_id, card_name=c_name, set_name=s_name, image_url=img_url)
                    st.session_state.user_wishlist = get_user_wishlist(user["id"])
                    st.toast("Added to Wishlist", icon="❤️")
                st.rerun(scope="fragment")

        st.divider()

    # --- FRAGMENT: LIBRARY ROW ---
    @st.fragment
    def render_library_row(item, card_data):
        c_preview, c_info, c_finish, c_qty = st.columns([1.8, 3.0, 1.5, 2.2])
        entry_id = item.get("id")
        
        card_name = item.get("card_name") or (card_data.get("name") if card_data else "Unknown Card")
        set_name = item.get("set_name") or (card_data.get("set_name") if card_data else "Unknown Set")
        img_url = item.get("image_url") or (get_card_image_url(card_data, size="large") if card_data else "")

        with c_preview:
            if img_url:
                st.image(img_url, use_container_width=True)

        with c_info:
            st.markdown(f"**{card_name}** · `{set_name}`")

        with c_finish:
            finish = item.get("finish", "nonfoil").capitalize()
            cond = item.get("condition", "NM")
            st.caption(f"**{finish}** ({cond})")

        with c_qty:
            q_dec, q_val, q_inc = st.columns([1, 1.2, 1], vertical_alignment="center")
            qty = item.get("quantity", 1)

            if q_dec.button("➖", key=f"dec_{entry_id}"):
                if qty - 1 <= 0:
                    remove_from_library(entry_id)
                    st.session_state.user_library = get_user_library(user["id"])
                    st.toast("Card removed", icon="🗑️")
                    st.rerun(scope="app")
                else:
                    update_library_card(entry_id, quantity=qty - 1)
                    item["quantity"] = qty - 1
                    st.rerun(scope="fragment")

            q_val.markdown(f"<p style='text-align: center; margin: 0;'><b>{qty}x</b></p>", unsafe_allow_html=True)

            if q_inc.button("➕", key=f"inc_{entry_id}"):
                update_library_card(entry_id, quantity=qty + 1)
                item["quantity"] = qty + 1
                st.rerun(scope="fragment")

        st.divider()

    # --- FRAGMENT: WISHLIST ROW ---
    @st.fragment
    def render_wishlist_row(wish_item, card_data, idx):
        c_preview, c_info, c_price, c_actions = st.columns([1.8, 3.0, 1.5, 2.2])
        scryfall_id = wish_item.get("scryfall_id")

        card_name = wish_item.get("card_name") or (card_data.get("name") if card_data else "Unknown Card")
        set_name = wish_item.get("set_name") or (card_data.get("set_name") if card_data else "Unknown Set")
        usd = card_data.get("prices", {}).get("usd") if card_data else "N/A"
        img_url = wish_item.get("image_url") or (get_card_image_url(card_data, size="large") if card_data else "")
        tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None

        with c_preview:
            if img_url:
                st.image(img_url, use_container_width=True)

        with c_info:
            st.markdown(f"**{card_name}** · `{set_name}`")

        with c_price:
            st.caption(f"Price: **${usd or 'N/A'}**")

        with c_actions:
            b_tcg, b_rem = st.columns(2)
            with b_tcg:
                if tcg_url:
                    st.link_button("🛒 TCG", tcg_url, use_container_width=True)
            with b_rem:
                if st.button("❌ Remove", key=f"rem_w_{scryfall_id}_{idx}", use_container_width=True):
                    remove_from_wishlist(user["id"], scryfall_id)
                    st.session_state.user_wishlist = get_user_wishlist(user["id"])
                    st.toast("Removed from Wishlist", icon="🗑️")
                    st.rerun(scope="app")

        st.divider()

    # --- TAB ROUTING ---
    if current_tab == "🔍 Search":
        st.subheader("Card Search")
        search_query = st.text_input("Search Scryfall...", placeholder="Type card name e.g. Sol Ring, Black Lotus...", key="scryfall_search")
        if search_query:
            results = search_cards(search_query)
            st.caption(f"Found **{len(results)}** printings")
            for idx, card in enumerate(results):
                render_search_row(card, idx)

    elif current_tab == "📚 Library":
        st.subheader("My Collection")
        lib_query = st.text_input("Filter Library...", placeholder="Search library by card name or set...", key="library_search").strip().lower()
        library_cards = [c for c in st.session_state.user_library if c.get("quantity", 0) > 0]
        
        filtered_library = []
        for item in library_cards:
            scryfall_id = item.get("scryfall_id")
            # Try DB text fields first, fall back to in-memory cache
            c_name = (item.get("card_name") or "").lower()
            s_name = (item.get("set_name") or "").lower()
            
            card_data = None
            if not c_name or not s_name:
                card_data = fetch_cached_card(scryfall_id)
                c_name = (card_data.get("name") if card_data else "").lower()
                s_name = (card_data.get("set_name") if card_data else "").lower()

            if not lib_query or lib_query in c_name or lib_query in s_name:
                filtered_library.append((item, card_data))

        st.caption(f"Showing **{len(filtered_library)}** of **{len(library_cards)}** entries")
        if not filtered_library:
            st.info("No matching cards in your library.")
        else:
            for item, card_data in filtered_library:
                render_library_row(item, card_data)

    elif current_tab == "❤️ Wishlist":
        st.subheader("My Wishlist")
        wish_query = st.text_input("Filter Wishlist...", placeholder="Search wishlist by card name or set...", key="wishlist_search").strip().lower()
        wishlist_items = st.session_state.user_wishlist
        
        filtered_wishlist = []
        for wish_item in wishlist_items:
            scryfall_id = wish_item.get("scryfall_id")
            c_name = (wish_item.get("card_name") or "").lower()
            s_name = (wish_item.get("set_name") or "").lower()
            
            card_data = None
            if not c_name or not s_name:
                card_data = fetch_cached_card(scryfall_id)
                c_name = (card_data.get("name") if card_data else "").lower()
                s_name = (card_data.get("set_name") if card_data else "").lower()

            if not wish_query or wish_query in c_name or wish_query in s_name:
                filtered_wishlist.append((wish_item, card_data))

        st.caption(f"Showing **{len(filtered_wishlist)}** of **{len(wishlist_items)}** items")
        if not filtered_wishlist:
            st.info("No matching items in your wishlist.")
        else:
            for idx, (wish_item, card_data) in enumerate(filtered_wishlist):
                render_wishlist_row(wish_item, card_data, idx)