import streamlit as st
import requests
from streamlit_searchbox import st_searchbox

from services.database import (
    create_user, get_user_by_username, get_user_by_email, verify_user_email,
    add_card_to_library, get_user_library, update_library_card, remove_from_library,
    add_to_wishlist, remove_from_wishlist, get_user_wishlist
)
from services.scryfall import search_cards, get_card_image_url, get_card_by_id
from utils.auth import hash_password, verify_password
from utils.tokens import generate_verification_token, verify_token

st.set_page_config(
    page_title="MTG Library App", 
    page_icon="🃏", 
    layout="wide",
    initial_sidebar_state="collapsed" if "user" not in st.session_state or st.session_state.user is None else "expanded"
)

# 1. Scryfall Autocomplete Function for st_searchbox
def search_scryfall_names(search_term: str) -> list[str]:
    """Fetches real-time autocomplete suggestions directly from Scryfall API."""
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

# 2. Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

if "active_search_label" not in st.session_state:
    st.session_state.active_search_label = ""
if "active_search_results" not in st.session_state:
    st.session_state.active_search_results = []
if "searchbox_key_counter" not in st.session_state:
    st.session_state.searchbox_key_counter = 0

# 3. Handle Verification Link in URL
query_params = st.query_params
if "verify_token" in query_params:
    token = query_params["verify_token"]
    verified_email = verify_token(token)
    if verified_email:
        verify_user_email(verified_email)
        st.success("Your email has been successfully verified! You can now log in.")
    else:
        st.error("Invalid or expired verification link.")
    st.query_params.clear()

# ==========================================
# UNAUTHENTICATED VIEW (Login / Register)
# ==========================================
if st.session_state.user is None:
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {display: none;}
            [data-testid="collapsedControl"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🃏 MTG Library App")
        tab_login, tab_register = st.tabs(["Login", "Register"])

        with tab_login:
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

        with tab_register:
            st.subheader("Create a new account")
            with st.form("register_form", clear_on_submit=False):
                reg_username = st.text_input("Username", key="reg_user")
                reg_email = st.text_input("Email Address", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_pass")
                reg_submitted = st.form_submit_button("Register", use_container_width=True)
            
            if reg_submitted:
                if not reg_username or not reg_email or not reg_password:
                    st.warning("Please fill in all fields.")
                elif get_user_by_username(reg_username):
                    st.error("Username already taken.")
                elif get_user_by_email(reg_email):
                    st.error("Email address already registered.")
                else:
                    pwd_hash, salt = hash_password(reg_password)
                    token = generate_verification_token(reg_email)
                    create_user(reg_username, reg_email, pwd_hash, salt, token)
                    st.success("Account created successfully!")
                    st.info(f"Verification token generated: `{token}`")

# ==========================================
# AUTHENTICATED VIEW (Search, Library & Wishlist)
# ==========================================
else:
    user = st.session_state.user

    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none;}
            .block-container { 
                padding-top: 2.5rem !important; 
                padding-bottom: 2rem !important;
                padding-left: 2rem !important;
                padding-right: 2rem !important;
                max-width: 98% !important;
            }
            header[data-testid="stHeader"] { background: transparent !important; z-index: 1 !important; }
            div[data-testid="stVerticalBlock"] { gap: 0.35rem !important; }
            .stButton button { padding: 0.2rem 0.5rem !important; font-size: 0.85rem !important; }
        </style>
    """, unsafe_allow_html=True)

    user_library = get_user_library(user["id"])
    user_wishlist = get_user_wishlist(user["id"])

    # --- SIDEBAR: NAVIGATION & SEARCH ---
    with st.sidebar:
        st.title(f"👤 {user['username']}")
        menu_selection = st.radio("Navigation", options=["Search", "My Library", "Wishlist"], index=0)
        st.divider()

        if menu_selection == "Search":
            st.markdown("### 🔍 Card Search")
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
                        st.rerun()

            st.divider()

        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # Helper function for parsing prices cleanly
    def parse_price(c):
        prices = c.get("prices", {}) if isinstance(c, dict) else {}
        p = prices.get("usd") or prices.get("usd_foil") or "0"
        try:
            return float(p)
        except (ValueError, TypeError):
            return 0.0

    # --- SCREEN 1: SEARCH ---
    if menu_selection == "Search":
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

                # Compact 3-Column Display Grid
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
                            set_name = card.get("set_name", "Unknown Set")
                            released_date = card.get("released_at", "")
                            st.caption(f"{set_name}")
                            st.caption(f"{released_date}")
                            
                            prices = card.get("prices", {})
                            usd = prices.get("usd")
                            usd_foil = prices.get("usd_foil")
                            st.caption(f"Reg: **\\${usd if usd else 'N/A'}** | Foil: **\\${usd_foil if usd_foil else 'N/A'}**")

                            valid_owned = [item for item in owned_entries if item.get("quantity", 0) > 0]
                            if valid_owned:
                                total_qty = sum(item.get("quantity", 0) for item in valid_owned)
                                st.caption(f"In Library: **{total_qty}x**")

                            # Add/Wishlist Controls
                            c1, c2 = st.columns(2)
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

    # --- SCREEN 2: MY LIBRARY ---
    elif menu_selection == "My Library":
        active_cards = [card for card in user_library if card.get("quantity", 0) > 0]
        
        st.subheader(f"My Library ({len(active_cards)} items)")
        
        if not active_cards:
            st.info("Your library is currently empty. Use Search to add cards!")
        else:
            # 1. Group active rows by scryfall_id
            grouped_library = {}
            for item in active_cards:
                sid = item.get("scryfall_id")
                if sid not in grouped_library:
                    grouped_library[sid] = []
                grouped_library[sid].append(item)

            # 2. Render cards in a 3-column grid
            cols = st.columns(3)
            for idx, (scryfall_id, variants) in enumerate(grouped_library.items()):
                col = cols[idx % 3]
                card_data = get_card_by_id(scryfall_id) if scryfall_id else None
                tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None
                total_qty = sum(v.get("quantity", 0) for v in variants)

                with col:
                    with st.container(border=True):
                        if card_data:
                            img_url = get_card_image_url(card_data, size="normal")
                            st.image(img_url, use_container_width=True)
                            if tcg_url:
                                st.markdown(f"**{card_data.get('name', 'Unknown')}** ([TCG]({tcg_url}))")
                            else:
                                st.markdown(f"**{card_data.get('name', 'Unknown')}**")
                            st.caption(f"Set: {card_data.get('set_name', 'Unknown')}")
                        else:
                            st.caption("Card details unavailable")

                        st.divider()

                        # 3. Render each unique variant (Finish + Condition)
                        for var in variants:
                            entry_id = var.get("id")
                            qty = var.get("quantity", 0)
                            finish = var.get("finish", "nonfoil").capitalize()
                            cond = var.get("condition", "Near Mint")

                            st.markdown(f"**{qty}x** {finish} (`{cond}`)")

                            c_dec, c_inc, c_edit = st.columns([1, 1, 1.2])
                            
                            with c_dec:
                                if st.button("➖ 1", key=f"lib_dec_{entry_id}", use_container_width=True):
                                    new_qty = qty - 1
                                    if new_qty <= 0:
                                        remove_from_library(entry_id)
                                        st.toast("Variant removed", icon="🗑️")
                                    else:
                                        update_library_card(entry_id, quantity=new_qty)
                                        st.toast(f"Updated quantity to {new_qty}", icon="📉")
                                    st.rerun()

                            with c_inc:
                                if st.button("➕ 1", key=f"lib_inc_{entry_id}", use_container_width=True):
                                    update_library_card(entry_id, quantity=qty + 1)
                                    st.toast(f"Updated quantity to {qty + 1}", icon="📈")
                                    st.rerun()

                        # 4. Add new condition/finish variant inline
                        with st.popover("➕ Add Variant", use_container_width=True):
                            new_finish = st.selectbox("Finish", ["nonfoil", "foil", "etched"], key=f"add_fin_{scryfall_id}")
                            new_cond = st.selectbox(
                                "Condition",
                                ["Near Mint", "Lightly Played", "Moderately Played", "Heavily Played", "Damaged"],
                                key=f"add_cond_{scryfall_id}"
                            )
                            new_qty = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"add_qty_{scryfall_id}")

                            if st.button("Add to Library", key=f"add_var_btn_{scryfall_id}", use_container_width=True):
                                add_card_to_library(
                                    user_id=user["id"],
                                    scryfall_id=scryfall_id,
                                    finish=new_finish,
                                    quantity=new_qty,
                                    condition=new_cond
                                )
                                st.toast("Added variant!", icon="✅")
                                st.rerun()

    # --- SCREEN 3: WISHLIST ---
    elif menu_selection == "Wishlist":
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