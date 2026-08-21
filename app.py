import streamlit as st
from services.database import create_user, get_user_by_username, get_user_by_email, verify_user_email
from services.scryfall import search_cards, get_card_image_url
from utils.auth import hash_password, verify_password
from utils.tokens import generate_verification_token, verify_token

st.set_page_config(
    page_title="MTG Library App", 
    page_icon="🃏", 
    layout="wide",
    initial_sidebar_state="collapsed" if "user" not in st.session_state or st.session_state.user is None else "expanded"
)

# 1. Dialog Modal to display Image and Full Scryfall JSON Payload
@st.dialog("Card Details", width="large")
def show_card_details(card: dict):
    img_url = get_card_image_url(card, size="large")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(img_url, use_container_width=True)
    with col2:
        st.subheader(card.get("name", "Card Details"))
        st.caption(f"**Set:** {card.get('set_name', '')} (`{card.get('set', '').upper()}`)")
    
    st.divider()
    st.subheader("Full Scryfall API Payload")
    st.json(card)  # Renders the full raw payload cleanly

# 2. Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

# ==========================================
# UNAUTHENTICATED VIEW
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
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", width="stretch"):
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
            reg_username = st.text_input("Username", key="reg_user")
            reg_email = st.text_input("Email Address", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_pass")
            if st.button("Register", width="stretch"):
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

# ==========================================
# AUTHENTICATED VIEW
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
        menu_selection = st.radio("Navigation", options=["Search", "My Collection"], index=0)
        st.divider()
        if st.button("Logout", width="stretch"):
            st.session_state.user = None
            st.rerun()

    # --- SEARCH SCREEN ---
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
                
                cols = st.columns(4)
                for idx, card in enumerate(results):
                    col = cols[idx % 4]
                    
                    with col:
                        img_url = get_card_image_url(card, size="large")
                        
                        # Display card image
                        st.image(img_url, use_container_width=True)
                        
                        # Set Name
                        set_name = card.get("set_name", "Unknown Set")
                        st.caption(f"Set: {set_name}")
                        
                        # Pricing
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
                        
                        # Clickable Trigger (Replaces 'View Details' button)
                        if st.button("🔎 View Payload", key=f"card_btn_{card['id']}_{idx}", width="stretch"):
                            show_card_details(card)

                        st.divider()

    elif menu_selection == "My Collection":
        st.title("📦 My Collection")
        st.info("Your collection inventory view will display here.")