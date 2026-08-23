import streamlit as st
from services.database import get_user_wishlist, remove_from_wishlist
from services.scryfall import get_card_by_id, get_card_image_url

st.set_page_config(page_title="My Wishlist", page_icon="❤️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: flex !important;}
        [data-testid="collapsedControl"] {display: flex !important;}
    </style>
""", unsafe_allow_html=True)

if "user" not in st.session_state or st.session_state.user is None:
    st.switch_page("app.py")

user = st.session_state.user
user_wishlist = get_user_wishlist(user["id"])

with st.sidebar:
    st.title(f"👤 {user['username']}")
    st.markdown("### Navigation")
    st.page_link("pages/01_search.py", label="Search", icon="🔍")
    st.page_link("pages/02_library.py", label="My Library", icon="📚")
    st.page_link("pages/03_wishlist.py", label="My Wishlist", icon="❤️")
    st.divider()

    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.switch_page("app.py")

st.subheader(f"❤️ My Wishlist ({len(user_wishlist)} items)")

if not user_wishlist:
    st.info("Your wishlist is empty. Use Search to add cards!")
else:
    cols = st.columns(3)
    for idx, scryfall_id in enumerate(user_wishlist):
        col = cols[idx % 3]
        card_data = get_card_by_id(scryfall_id)
        tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None

        with col:
            with st.container(border=True):
                if card_data:
                    img_url = get_card_image_url(card_data, size="normal")
                    st.image(img_url, use_container_width=True)
                    st.markdown(f"**{card_data.get('name', 'Unknown Card')}**")
                    st.caption(f"Set: {card_data.get('set_name', 'Unknown')}")
                    prices = card_data.get("prices", {})
                    st.caption(f"Price: **${prices.get('usd', 'N/A')}**")
                else:
                    st.caption("Card details unavailable")

                c_rem, c_tcg = st.columns(2)
                with c_rem:
                    if st.button("❌ Remove", key=f"rem_wish_{scryfall_id}_{idx}", use_container_width=True):
                        remove_from_wishlist(user["id"], scryfall_id)
                        st.toast("Removed from Wishlist", icon="🗑️")
                        st.rerun()
                with c_tcg:
                    if tcg_url:
                        st.link_button("🛒 TCGPlayer", tcg_url, use_container_width=True)