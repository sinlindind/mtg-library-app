import streamlit as st
import requests

from services.database import (
    get_user_by_username,
    get_user_library,
    get_user_wishlist,
    add_card_to_library,
    add_to_wishlist,
    remove_from_wishlist
)
from services.scryfall import search_cards, get_card_image_url
from utils.auth import verify_password

st.set_page_config(page_title="MTG Hub", page_icon="🃏", layout="wide", initial_sidebar_state="collapsed")

# Hide standard sidebar completely
st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
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
            st.session_state.user = None
            st.rerun()

    st.divider()

    # --- TAB ROUTING ---
    if current_tab == "🔍 Search":
        st.subheader("Card Search")
        search_query = st.text_input("Search Scryfall...", placeholder="Type card name...")
        if search_query:
            results = search_cards(search_query)
            st.write(f"Found {len(results)} printings:")
            for card in results[:5]:  # Display snippet
                st.write(f"- **{card.get('name')}** ({card.get('set_name')})")

    elif current_tab == "📚 Library":
        st.subheader("My Collection")
        library_cards = get_user_library(user["id"])
        st.write(f"Total entries: {len(library_cards)}")

    elif current_tab == "❤️ Wishlist":
        st.subheader("My Wishlist")
        wishlist_cards = get_user_wishlist(user["id"])
        st.write(f"Total wishlist items: {len(wishlist_cards)}")