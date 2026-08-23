import streamlit as st
from services.database import get_user_by_username, get_user_by_email, create_user, verify_user_email
from utils.auth import hash_password, verify_password
from utils.tokens import generate_verification_token, verify_token

st.set_page_config(
    page_title="MTG Library App", 
    page_icon="🃏", 
    layout="wide"
)

# Initialize Session States
if "user" not in st.session_state:
    st.session_state.user = None

# Handle Verification Link in URL
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

# If User is logged in, redirect straight to Search page
if st.session_state.user:
    st.switch_page("pages/01_search.py")

# UNAUTHENTICATED VIEW (Login / Register)
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
                    st.switch_page("pages/01_search.py")
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