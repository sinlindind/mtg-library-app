import streamlit as st
from services.database import get_user_library, get_user_wishlist
from services.scryfall import search_cards

st.set_page_config(page_title="MTG Library", page_icon="🃏", layout="wide", initial_sidebar_state="collapsed")

# Hide standard sidebar completely
st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    </style>
""", unsafe_allow_html=True)

if "user" not in st.session_state or st.session_state.user is None:
    st.switch_page("app.py")

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
        st.switch_page("app.py")

st.divider()

# --- CONTENT ROUTING ---
if current_tab == "🔍 Search":
    st.markdown("#### Card Search")
    # Search implementation goes here...

elif current_tab == "📚 Library":
    st.markdown("#### My Collection")
    # Library view implementation goes here...

elif current_tab == "❤️ Wishlist":
    st.markdown("#### Wishlist")
    # Wishlist implementation goes here...