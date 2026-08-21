import streamlit as st
from services.database import (
    create_user, get_user_by_username, get_user_by_email, verify_user_email,
    add_card_to_library, get_user_library
)
from services.scryfall import search_cards, get_card_image_url
from utils.auth import hash_password, verify_password
from utils.tokens import generate_verification_token, verify_token

st.set_page_config(
    page_title="MTG Library App", 
    page_icon="🃏", 
    layout="wide",
    initial_sidebar_state="collapsed" if "user" not in st.session_state or st.session_state.user is None else "expanded"
)

# Helper function to mutate card quantities safely in session_state
def adjust_quantity(card_id: str, field: str, amount: int):
    key = f"{card_id}_{field}"
    current_val = st.session_state.get(key, 0)
    st.session_state[key] = max(0, current_val + amount)

# 1. Dialog Modal to display Image and Full Scryfall JSON Payload
@st.dialog("Card Details", width="large")
def show_card_details(card: dict):
    img_url = get_card_image_url(card, size="large")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(img_url, width='stretch')
    with col2:
        st.subheader(card.get("name", "Card Details"))
        st.caption(f"**Set:** {card.get('set_name', '')} (`{card.get('set', '').upper()}`)")
    
    st.divider()
    st.subheader("Full Scryfall API Payload")
    st.json(card)

# 2. Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

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

        # LOGIN TAB
        with tab_login:
            st.subheader("Login to your account")
            with st.form("login_form", clear_on_submit=False):
                login_username = st.text_input("Username", key="login_user")
                login_password = st.text_input("Password", type="password", key="login_pass")
                login_submitted = st.form_submit_button("Login", width='stretch')
            
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

        # REGISTER TAB
        with tab_register:
            st.subheader("Create a new account")
            with st.form("register_form", clear_on_submit=False):
                reg_username = st.text_input("Username", key="reg_user")
                reg_email = st.text_input("Email Address", key="reg_email")
                reg_password = st.text_input("Password", type="password", key="reg_pass")
                reg_submitted = st.form_submit_button("Register", width='stretch')
            
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
        if st.button("Logout", width='stretch'):
            st.session_state.user = None
            st.rerun()

    # --- SCREEN 1: SEARCH ---
    if menu_selection == "Search":
        st.title("🔍 MTG Card Search")
        
        search_query = st.text_input(
            "Search Scryfall", 
            placeholder="Enter card name or syntax (e.g. 'Sol Ring')"
        )

        if search_query:
            with st.spinner("Searching Scryfall..."):
                results = search_cards(search_query)
            
            if not results:
                st.warning("No cards found matching your query.")
            else:
                st.success(f"Found **{len(results)}** printings")
                
                # 4-Column Grid
                cols = st.columns(4)
                for idx, card in enumerate(results):
                    col = cols[idx % 4]
                    card_id = f"{card['id']}_{idx}"
                    
                    # Initialize counter state keys
                    if f"{card_id}_reg" not in st.session_state:
                        st.session_state[f"{card_id}_reg"] = 0
                    if f"{card_id}_foil" not in st.session_state:
                        st.session_state[f"{card_id}_foil"] = 0

                    with col:
                        img_url = get_card_image_url(card, size="large")
                        
                        # 1. High-Resolution Card Artwork
                        st.image(img_url, width='stretch')
                        
                        # 2. Set Name Caption
                        set_name = card.get("set_name", "Unknown Set")
                        st.caption(f"Set: {set_name}")
                        
                        # 3. Pricing Caption
                        prices = card.get("prices", {})
                        usd = prices.get("usd")
                        usd_foil = prices.get("usd_foil")
                        
                        price_parts = []
                        if usd:
                            price_parts.append(f"Reg: \\${usd}")
                        if usd_foil:
                            price_parts.append(f"Foil: \\${usd_foil}")
                            
                        price_line = " \\| ".join(price_parts) if price_parts else "No pricing available"
                        st.caption(price_line)
                        
                        # 4. Details Button (Renamed from Payload)
                        if st.button("🔍 Details", key=f"details_btn_{card_id}", width='stretch'):
                            show_card_details(card)

                        st.write("") # Line spacing

                        # 5. Regular Quantity Selector Row (+ / -)
                        col_lbl_r, col_minus_r, col_val_r, col_plus_r = st.columns([2, 1, 1, 1])
                        with col_lbl_r:
                            st.markdown("**Regular:**")
                        with col_minus_r:
                            st.button("➖", key=f"minus_reg_{card_id}", on_click=adjust_quantity, args=(card_id, "reg", -1), width='stretch')
                        with col_val_r:
                            st.markdown(f"<h4 style='text-align: center; margin: 0;'>{st.session_state[f'{card_id}_reg']}</h4>", unsafe_allow_html=True)
                        with col_plus_r:
                            st.button("➕", key=f"plus_reg_{card_id}", on_click=adjust_quantity, args=(card_id, "reg", 1), width='stretch')

                        # Line Feed between Reg and Foil
                        st.write("")

                        # 6. Foil Quantity Selector Row (+ / -)
                        col_lbl_f, col_minus_f, col_val_f, col_plus_f = st.columns([2, 1, 1, 1])
                        with col_lbl_f:
                            st.markdown("**Foil:**")
                        with col_minus_f:
                            st.button("➖", key=f"minus_foil_{card_id}", on_click=adjust_quantity, args=(card_id, "foil", -1), width='stretch')
                        with col_val_f:
                            st.markdown(f"<h4 style='text-align: center; margin: 0;'>{st.session_state[f'{card_id}_foil']}</h4>", unsafe_allow_html=True)
                        with col_plus_f:
                            st.button("➕", key=f"plus_foil_{card_id}", on_click=adjust_quantity, args=(card_id, "foil", 1), width='stretch')

                        st.divider()

    # --- SCREEN 2: MY LIBRARY ---
    elif menu_selection == "My Library":
        st.title("📦 My Master Library")
        
        library_cards = get_user_library(user["id"])
        if not library_cards:
            st.info("Your library is currently empty. Use Search to add cards!")
        else:
            st.success(f"Total unique printings in library: **{len(library_cards)}**")
            st.dataframe(library_cards, width='stretch')