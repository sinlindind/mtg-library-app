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

# 1. Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

# 2. Handle Verification Link in URL
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
# UNAUTHENTICATED VIEW (Clean Centered Screen)
# ==========================================
if st.session_state.user is None:
    # CSS snippet to completely hide sidebar and toggle controls on initial screen
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
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Login", use_container_width=True):
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
            reg_username = st.text_input("Username", key="reg_user")
            reg_email = st.text_input("Email Address", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_pass")
            
            if st.button("Register", use_container_width=True):
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
# AUTHENTICATED VIEW (Search & Collection)
# ==========================================
else:
    user = st.session_state.user

    # Sidebar Navigation Menu
    with st.sidebar:
        st.title(f"👤 {user['username']}")
        
        # Default menu view is 'Search'
        menu_selection = st.radio(
            "Navigation", 
            options=["Search", "My Collection"],
            index=0
        )
        st.divider()
        if st.button("Logout", use_container_width=True):
            st.session_state.user = None
            st.rerun()

    # --- SCREEN 1: SEARCH (Default) ---
    if menu_selection == "Search":
        st.title("🔍 MTG Card Search")
        
        search_query = st.text_input(
            "Search Scryfall", 
            placeholder="Enter card name or syntax (e.g. 'Sol Ring' or '!'Sol Ring'')"
        )

        if search_query:
            with st.spinner("Searching Scryfall..."):
                results = search_cards(search_query)
            
            if not results:
                st.warning("No cards found matching your query.")
            else:
                st.success(f"Found **{len(results)} versions/printings")
                
                # 4-Column Grid
                cols = st.columns(4)
                
                for idx, card in enumerate(results):
                    col = cols[idx % 4]
                    
                    with col:
                        # Card Artwork
                        img_url = get_card_image_url(card, size="large")
                        st.image(img_url, use_container_width=True)
                        
                        # 1. Extract Set Name
                        set_name = card.get("set_name", "Unknown Set")
                        
                        # 2. Extract Prices
                        prices = card.get("prices", {})
                        usd = prices.get("usd")
                        usd_foil = prices.get("usd_foil")
                        
                        price_parts = []
                        if usd:
                            price_parts.append(f"Reg: ${usd}")
                        if usd_foil:
                            price_parts.append(f"Foil: ${usd_foil}")
                            
                        price_text = " | ".join(price_parts) if price_parts else "No pricing available"
                        
                        # 3. Clean Single Caption (Set Name + Prices)
                        st.caption(f"Set: {set_name}\n{price_text}")
                        
                        # View Details Popover
                        with st.popover("View Details", use_container_width=True):
                            set_code = card.get("set", "").upper()
                            cn = card.get("collector_number", "")
                            
                            st.subheader(f"{card['name']} ({set_code} #{cn})")
                            st.write(f"**Type:** {card.get('type_line', 'N/A')}")
                            st.write(f"**Mana Cost:** {card.get('mana_cost', 'N/A')}")
                            st.divider()
                            
                            oracle_text = card.get("oracle_text")
                            if not oracle_text and "card_faces" in card:
                                oracle_text = "\n\n---\n\n".join(
                                    f"**{face.get('name')}**\n{face.get('oracle_text', '')}"
                                    for face in card["card_faces"]
                                )
                            
                            st.markdown(f"**Oracle Text:**\n\n{oracle_text or 'No card text.'}")
                            
                            if "flavor_text" in card:
                                st.caption(f"_{card['flavor_text']}_")
                                
                            st.write(f"**Artist:** {card.get('artist', 'Unknown')}")

                        st.divider()

    # --- SCREEN 2: MY COLLECTION ---
    elif menu_selection == "My Collection":
        st.title("📦 My Collection")
        st.info("Your collection functionality will display here.")