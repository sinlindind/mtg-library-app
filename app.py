import streamlit as st
import streamlit.components.v1 as components
import json
import requests

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

# 1. Custom JavaScript Autocomplete Search Component
def scryfall_autocomplete_box(key="mtg_search"):
    """
    Renders an HTML input with a native <datalist> dropdown. 
    Queries Scryfall directly in JS as you type, preserving cursor focus completely.
    Only passes the final selection back to Streamlit on selection/Enter.
    """
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: transparent;
        }}
        .search-container {{
            width: 100%;
            position: relative;
        }}
        input {{
            width: 100%;
            padding: 10px 14px;
            font-size: 16px;
            border: 1px solid #4a4a4a;
            border-radius: 8px;
            background-color: #262730;
            color: #ffffff;
            box-sizing: border-box;
            outline: none;
        }}
        input:focus {{
            border-color: #ff4b4b;
            box-shadow: 0 0 0 1px #ff4b4b;
        }}
      </style>
    </head>
    <body>
      <div class="search-container">
        <input 
            type="text" 
            id="mtgInput" 
            list="scryfallList" 
            placeholder="Type a card name (e.g. 'Sol Ring')..." 
            autocomplete="off"
        />
        <datalist id="scryfallList"></datalist>
      </div>

      <script>
        // Streamlit Component API initialization
        function sendMessageToStreamlit(value) {{
            window.parent.postMessage({{
                type: "streamlit:setComponentValue",
                value: value
            }}, "*");
        }}

        const input = document.getElementById('mtgInput');
        const datalist = document.getElementById('scryfallList');
        let timer = null;

        // Fetch live suggestions from Scryfall on input
        input.addEventListener('input', function(e) {{
            const query = e.target.value.trim();
            
            // Send value back if user picked an exact option from datalist
            const options = Array.from(datalist.options).map(opt => opt.value);
            if (options.includes(query)) {{
                sendMessageToStreamlit(query);
                return;
            }}

            if (query.length < 2) {{
                datalist.innerHTML = '';
                return;
            }}

            // Debounce API calls to prevent flooding Scryfall
            clearTimeout(timer);
            timer = setTimeout(() => {{
                fetch(`https://api.scryfall.com/cards/autocomplete?q=${{encodeURIComponent(query)}}`)
                    .then(res => res.json())
                    .then(data => {{
                        if (data && data.data) {{
                            datalist.innerHTML = data.data
                                .map(item => `<option value="${{item}}">`)
                                .join('');
                        }}
                    }})
                    .catch(() => {{}});
            }}, 150);
        }});

        // Trigger search when pressing Enter
        input.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') {{
                sendMessageToStreamlit(input.value.trim());
            }}
        }});

        // Tell Streamlit how tall this component frame is
        window.addEventListener('load', () => {{
            window.parent.postMessage({{
                type: "streamlit:setFrameHeight",
                height: 50
            }}, "*");
        }});
      </script>
    </body>
    </html>
    """
    return components.html(html_code, height=50, key=key)

# 2. Dialog Modal for Card Details
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
    st.json(card)

# 3. Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

# 4. Handle Verification Link in URL
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

        # REGISTER TAB
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
        
        # Native JS Autocomplete Search Box Component
        search_query = scryfall_autocomplete_box(key="main_mtg_search")

        if search_query and len(search_query.strip()) >= 2:
            with st.spinner(f"Searching printings for '{search_query}'..."):
                results = search_cards(search_query.strip())
            
            if not results:
                st.warning("No cards found matching your query.")
            else:
                st.success(f"Found **{len(results)}** printings")
                
                for idx, card in enumerate(results):
                    card_id = f"{card['id']}_{idx}"
                    owned_entries = [item for item in user_library if item.get("scryfall_id") == card["id"]]
                    
                    col_img, col_info, col_actions = st.columns([1.5, 2.5, 2])
                    
                    # COLUMN 1: Image
                    with col_img:
                        img_url = get_card_image_url(card, size="large")
                        st.image(img_url, use_container_width=True)
                    
                    # COLUMN 2: Details & Library Ownership
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
                    
                    # COLUMN 3: Quick Add Controls
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
                item_id = f"{item.get('id', idx)}"
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