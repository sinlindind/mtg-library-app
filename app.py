import streamlit as st
from services.database import create_user, get_user_by_username, get_user_by_email, verify_user_email
from utils.auth import hash_password, verify_password
from utils.tokens import generate_verification_token, verify_token

st.set_page_config(page_title="MTG Library App", page_icon="🃏", layout="wide")

# 1. Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

# 2. Check for Email Verification Link in Query Parameters
query_params = st.query_params
if "verify_token" in query_params:
    token = query_params["verify_token"]
    verified_email = verify_token(token)
    if verified_email:
        verify_user_email(verified_email)
        st.success("Your email has been successfully verified! You can now log in.")
    else:
        st.error("Invalid or expired verification link.")
    # Clear query parameters
    st.query_params.clear()

# 3. Main App Navigation
if st.session_state.user:
    # --- LOGGED IN USER INTERFACE ---
    user = st.session_state.user
    st.sidebar.title(f"Welcome, {user['username']}!")
    
    if not user.get("is_verified", False):
        st.warning("⚠️ Your email is unverified. Please check your inbox or request a new verification email.")
        if st.button("Resend Verification Link"):
            # Email service trigger goes here
            st.info("Verification link resent!")

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    st.title("📚 MTG Library Dashboard")
    st.write("Welcome to your collection manager.")

else:
    # --- AUTHENTICATION INTERFACE ---
    st.title("🃏 MTG Library App")
    
    tab_login, tab_register = st.tabs(["Login", "Register"])

    # LOGIN TAB
    with tab_login:
        st.subheader("Login to your account")
        login_username = st.text_input("Username", key="login_user")
        login_password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Login"):
            user_record = get_user_by_username(login_username)
            if user_record:
                # Split stored "hash:salt" string
                stored_hash, stored_salt = user_record["password_hash"].split(":")
                if verify_password(login_password, stored_hash, stored_salt):
                    st.session_state.user = user_record
                    st.success("Logged in successfully!")
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
        
        if st.button("Register"):
            if not reg_username or not reg_email or not reg_password:
                st.warning("Please fill in all fields.")
            elif get_user_by_username(reg_username):
                st.error("Username already taken.")
            elif get_user_by_email(reg_email):
                st.error("Email address already registered.")
            else:
                # Hash password and create verification token
                pwd_hash, salt = hash_password(reg_password)
                token = generate_verification_token(reg_email)
                
                # Save to Supabase
                create_user(reg_username, reg_email, pwd_hash, salt, token)
                
                st.success("Account created successfully!")
                st.info(f"Verification token generated: `{token}` (Use this to test your email verification link).")