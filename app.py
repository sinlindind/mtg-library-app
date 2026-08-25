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

# Custom CSS for compact layout, proper padding, and zero clipping
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

        /* 5. Standardize button heights and vertical alignment */
        div.stButton > button {
            height: 2.25rem !important;
            padding: 0 0.5rem !important;
            font-size: 0.85rem !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }

        /* 6. Standardize segmented control height */
        div[data-testid="stSegmentedControl"] {
            min-height: 2.25rem !important;
        }

        /* Compact row styling */
        .card-row {
            display: flex;
            align-items: center;
            border-bottom: 1px solid #2e303e;
            padding: 0.4rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

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
        c_preview, c_info, c_price, c_actions = st.columns([0.8, 3.5, 1.5, 2.2], vertical_alignment="center")
        img_url = get_card_image_url(card, size="normal")
        usd = card.get("prices", {}).get("usd") or "N/A"
        usd_foil = card.get("prices", {}).get("usd_foil") or "N/A"
        card_id = card["id"]

        with c_preview:
            with st.popover("🖼️ View", use_container_width=True):
                st.image(img_url, use_container_width=True)

        with c_info:
            st.markdown(f"**{card.get('name')}** · `{card.get('set_name')}`")

        with c_price:
            st.caption(f"Reg: **${usd}** | Foil: **${usd_foil}**")

        with c_actions:
            b1, b2, b3 = st.columns(3)
            if b1.button("➕ Reg", key=f"add_reg_{card_id}_{idx}"):
                add_card_to_library(user["id"], card_id, "nonfoil", 1, "Near Mint", float(usd) if usd != "N/A" else None)
                st.session_state.user_library = get_user_library(user["id"])
                st.toast(f"Added {card.get('name')} (Reg)", icon="✅")

            if b2.button("✨ Foil", key=f"add_foil_{card_id}_{idx}"):
                add_card_to_library(user["id"], card_id, "foil", 1, "Near Mint", float(usd_foil) if usd_foil != "N/A" else None)
                st.session_state.user_library = get_user_library(user["id"])
                st.toast(f"Added {card.get('name')} (Foil)", icon="✨")

            is_in_wishlist = card_id in st.session_state.user_wishlist
            wish_label = "❤️" if is_in_wishlist else "🤍"
            if b3.button(wish_label, key=f"wish_{card_id}_{idx}"):
                if is_in_wishlist:
                    remove_from_wishlist(user["id"], card_id)
                    st.session_state.user_wishlist.remove(card_id)
                    st.toast("Removed from Wishlist", icon="🗑️")
                else:
                    add_to_wishlist(user["id"], card_id)
                    st.session_state.user_wishlist.append(card_id)
                    st.toast("Added to Wishlist", icon="❤️")
                st.rerun(scope="fragment")

    # --- FRAGMENT: LIBRARY ROW ---
    @st.fragment
    def render_library_row(item):
        c_preview, c_info, c_finish, c_qty = st.columns([0.8, 3.5, 1.5, 2.2], vertical_alignment="center")
        entry_id = item.get("id")
        scryfall_id = item.get("scryfall_id")
        card_data = get_card_by_id(scryfall_id) if scryfall_id else None
        
        card_name = card_data.get("name", "Unknown Card") if card_data else "Unknown Card"
        set_name = card_data.get("set_name", "Unknown Set") if card_data else "Unknown Set"
        img_url = get_card_image_url(card_data, size="normal") if card_data else ""

        with c_preview:
            with st.popover("🖼️ View", use_container_width=True):
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

    # --- FRAGMENT: WISHLIST ROW ---
    @st.fragment
    def render_wishlist_row(scryfall_id, idx):
        c_preview, c_info, c_price, c_actions = st.columns([0.8, 3.5, 1.5, 2.2], vertical_alignment="center")
        card_data = get_card_by_id(scryfall_id) if scryfall_id else None

        card_name = card_data.get("name", "Unknown Card") if card_data else "Unknown Card"
        set_name = card_data.get("set_name", "Unknown Set") if card_data else "Unknown Set"
        usd = card_data.get("prices", {}).get("usd") or "N/A" if card_data else "N/A"
        img_url = get_card_image_url(card_data, size="normal") if card_data else ""
        tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None

        with c_preview:
            with st.popover("🖼️ View", use_container_width=True):
                if img_url:
                    st.image(img_url, use_container_width=True)

        with c_info:
            st.markdown(f"**{card_name}** · `{set_name}`")

        with c_price:
            st.caption(f"Price: **${usd}**")

        with c_actions:
            b_tcg, b_rem = st.columns(2)
            with b_tcg:
                if tcg_url:
                    st.link_button("🛒 TCG", tcg_url, use_container_width=True)
            with b_rem:
                if st.button("❌ Remove", key=f"rem_w_{scryfall_id}_{idx}", use_container_width=True):
                    remove_from_wishlist(user["id"], scryfall_id)
                    st.session_state.user_wishlist.remove(scryfall_id)
                    st.toast("Removed from Wishlist", icon="🗑️")
                    st.rerun(scope="app")

    # --- TAB ROUTING ---
    if current_tab == "🔍 Search":
        st.subheader("Card Search")
        search_query = st.text_input("Search Scryfall...", placeholder="Type card name e.g. Sol Ring, Black Lotus...")
        if search_query:
            results = search_cards(search_query)
            st.caption(f"Found **{len(results)}** printings")
            for idx, card in enumerate(results):
                render_search_row(card, idx)

    elif current_tab == "📚 Library":
        st.subheader("My Collection")
        library_cards = [c for c in st.session_state.user_library if c.get("quantity", 0) > 0]
        st.caption(f"Total entries: **{len(library_cards)}**")
        if not library_cards:
            st.info("Your library is empty. Use Search to add cards!")
        else:
            for item in library_cards:
                render_library_row(item)

    elif current_tab == "❤️ Wishlist":
        st.subheader("My Wishlist")
        wishlist_ids = st.session_state.user_wishlist
        st.caption(f"Total items: **{len(wishlist_ids)}**")
        if not wishlist_ids:
            st.info("Your wishlist is empty. Use Search to add cards!")
        else:
            for idx, scryfall_id in enumerate(wishlist_ids):
                render_wishlist_row(scryfall_id, idx)