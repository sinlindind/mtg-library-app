import streamlit as st
import requests
from streamlit_searchbox import st_searchbox

from services.database import (
    create_user, get_user_by_username, get_user_by_email, verify_user_email,
    add_card_to_library, get_user_library
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

# Search state persistence and input clear control
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
# AUTHENTICATED VIEW (Search & Library)
# ==========================================
else:
    user = st.session_state.user

    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.title(f"👤 {user['username']}")
        menu_selection = st.radio("Navigation", options=["Search", "My Library"], index=0)
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # --- SCREEN 1: SEARCH ---
    if menu_selection == "Search":
        st.title("🔍 MTG Card Search")
        
        user_library = get_user_library(user["id"])
        
        # Native JS Autocomplete Search Box with dynamic key to auto-clear on select
        current_search_key = f"scryfall_autocomplete_box_{st.session_state.searchbox_key_counter}"
        search_selection = st_searchbox(
            search_scryfall_names,
            placeholder="Type a card name (e.g. 'Sol Ring')...",
            key=current_search_key
        )
        
        # Process new selection, save active results, then clear the input box
        if search_selection and len(search_selection.strip()) >= 2:
            query = search_selection.strip()
            with st.spinner(f"Searching printings for '{query}'..."):
                results = search_cards(query)
                st.session_state.active_search_label = query
                st.session_state.active_search_results = results
                st.session_state.searchbox_key_counter += 1
                st.rerun()

        # Display the active search query label and saved search results
        if st.session_state.active_search_label:
            st.subheader(f"Results for: **{st.session_state.active_search_label}**")
            results = st.session_state.active_search_results
            
            if not results:
                st.warning("No cards found matching your query.")
            else:
                st.success(f"Found **{len(results)}** printings")
                
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
        st.title("📦 My Library")
        
        library_cards = get_user_library(user["id"])
        active_cards = [card for card in library_cards if card.get("quantity", 0) > 0]
        
        if not active_cards:
            st.info("Your library is currently empty. Use Search to add cards!")
        else:
            st.success(f"Total entries in library: **{len(active_cards)}**")
            
            for idx, item in enumerate(active_cards):
                scryfall_id = item.get("scryfall_id")
                card_data = get_card_by_id(scryfall_id) if scryfall_id else None
                
                col_img, col_info, col_actions = st.columns([1, 2, 2])
                
                with col_img:
                    if card_data:
                        img_url = get_card_image_url(card_data, size="small")
                        st.image(img_url, width=150)
                    else:
                        st.caption("No image available")
                
                with col_info:
                    card_name = card_data.get("name", "Unknown Card") if card_data else "Unknown Card"
                    st.subheader(card_name)
                    
                    if card_data:
                        set_name = card_data.get("set_name", "Unknown Set")
                        set_code = card_data.get("set", "").upper()
                        st.markdown(f"**Set:** {set_name} (`{set_code}`)")
                    
                    qty = item.get("quantity", 0)
                    finish = item.get("finish", "nonfoil").capitalize()
                    cond = item.get("condition", "Near Mint")
                    
                    st.markdown("---")
                    st.markdown(f"• **{qty}x** {finish} ({cond})")
                
                with col_actions:
                    st.empty()
                
                st.divider()