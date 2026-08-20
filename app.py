import hashlib
import math
import pandas as pd
import requests
import streamlit as st
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="MTG Library Manager", layout="wide")

HEADERS = {"User-Agent": "MyMTGDataEntryApp/1.0", "Accept": "*/*"}

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)


def hash_password(password: str) -> str:
    """Hashes passwords using SHA-256 for secure storage."""
    return hashlib.sha256(password.encode()).hexdigest()


def load_users() -> pd.DataFrame:
    """Reads the Users worksheet from Google Sheets."""
    df = conn.read(worksheet="Users", ttl=0)
    if df.empty or "username" not in df.columns:
        return pd.DataFrame(columns=["username", "password_hash"])
    return df


# --- SESSION STATE INITIALIZATION ---
if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

# --- AUTHENTICATION SIDEBAR ---
st.sidebar.title("User Portal")

if st.session_state.logged_in_user:
    st.sidebar.success(f"Logged in as **{st.session_state.logged_in_user}**")
    if st.sidebar.button("Log Out"):
        st.session_state.logged_in_user = None
        st.rerun()
else:
    auth_mode = st.sidebar.radio("Select Action", ["Login", "Register"])
    username_input = st.sidebar.text_input("Username").strip().lower()
    password_input = st.sidebar.text_input("Password", type="password")

    users_df = load_users()

    if auth_mode == "Login":
        if st.sidebar.button("Log In"):
            if not username_input or not password_input:
                st.sidebar.error("Please fill in both fields.")
            elif users_df.empty:
                st.sidebar.error("No registered users found.")
            else:
                hashed_pw = hash_password(password_input)
                match = users_df[
                    (users_df["username"] == username_input)
                    & (users_df["password_hash"] == hashed_pw)
                ]
                if not match.empty:
                    st.session_state.logged_in_user = username_input
                    st.rerun()
                else:
                    st.sidebar.error("Invalid username or password.")

    elif auth_mode == "Register":
        if st.sidebar.button("Create Account"):
            if not username_input or not password_input:
                st.sidebar.error("Please fill in both fields.")
            elif (
                not users_df.empty
                and username_input in users_df["username"].values
            ):
                st.sidebar.error("Username already taken.")
            else:
                new_user = pd.DataFrame([
                    {
                        "username": username_input,
                        "password_hash": hash_password(password_input),
                    }
                ])
                updated_df = pd.concat(
                    [users_df, new_user], ignore_index=True
                )
                conn.update(worksheet="Users", data=updated_df)
                st.sidebar.success("Account created! You can now log in.")


# --- MAIN APP DISPLAY ---
if not st.session_state.logged_in_user:
    st.title("MTG Library Manager")
    st.info("👈 Please log in or register via the sidebar to access the card search.")

else:
    st.title(f"Welcome, {st.session_state.logged_in_user.title()}!")

    # --- SCRYFALL API HELPER ---
    @st.cache_data(ttl=3600)
    def fetch_all_printings(card_name):
        url = "https://api.scryfall.com/cards/search"
        params = {"q": f'!"{card_name}"', "unique": "prints"}
        response = requests.get(url, params=params, headers=HEADERS)
        if response.status_code == 200:
            return response.json().get("data", [])
        return []

    # --- MODAL DIALOG ---
    @st.dialog("Card Details", width="large")
    def show_card_details(card):
        col1, col2 = st.columns([1, 2])
        with col1:
            img_url = (
                card.get("image_uris", {}).get("large")
                or card.get("image_uris", {}).get("normal")
                or (
                    card["card_faces"][0]["image_uris"]["large"]
                    if "card_faces" in card
                    else None
                )
            )
            if img_url:
                st.image(img_url, use_container_width=True)

        with col2:
            st.subheader(f"{card.get('name')} [{card.get('set').upper()}]")
            st.write(f"**Set Name:** {card.get('set_name')}")
            st.write(f"**Collector Number:** #{card.get('collector_number')}")
            st.write(f"**Released:** {card.get('released_at')}")
            st.write(f"**Rarity:** {card.get('rarity').title()}")

            prices = card.get("prices", {})
            st.write(f"**USD Price:** ${prices.get('usd') or 'N/A'}")
            st.write(f"**Foil Price:** ${prices.get('usd_foil') or 'N/A'}")

            with st.expander("View Full Raw JSON"):
                st.json(card)

        if st.button("Close"):
            st.rerun()

    # --- SEARCH BAR ---
    search_col, _ = st.columns([3, 1])
    with search_col:
        card_input = st.text_input("Enter exact card name:", value="Sol Ring")

    if card_input:
        printings = fetch_all_printings(card_input)

        if not printings:
            st.warning(f"No printings found for '{card_input}'.")
        else:
            # --- PAGINATION & PER PAGE CONTROLS ---
            pag_col1, pag_col2, _ = st.columns([2, 2, 4])

            temp_per_page = 12
            temp_total_pages = math.ceil(len(printings) / temp_per_page)

            with pag_col1:
                page = st.number_input(
                    "Page:",
                    min_value=1,
                    max_value=max(1, temp_total_pages),
                    value=1,
                    step=1,
                )

            with pag_col2:
                cards_per_page = st.selectbox(
                    "Cards per page:", options=[12, 24, 48, 96], index=0
                )

            total_cards = len(printings)
            total_pages = math.ceil(total_cards / cards_per_page)

            start_idx = (page - 1) * cards_per_page
            end_idx = start_idx + cards_per_page
            page_cards = printings[start_idx:end_idx]

            st.caption(
                f"Page {page} of {total_pages} | Showing {start_idx + 1}-{min(end_idx, total_cards)} of {total_cards} printings"
            )

            # --- GRID DISPLAY ---
            GRID_COLUMNS = 4
            for i in range(0, len(page_cards), GRID_COLUMNS):
                cols = st.columns(GRID_COLUMNS)
                row_cards = page_cards[i : i + GRID_COLUMNS]

                for idx, item in enumerate(row_cards):
                    with cols[idx]:
                        img_url = (
                            item.get("image_uris", {}).get("normal")
                            or item.get("image_uris", {}).get("small")
                            or (
                                item["card_faces"][0]["image_uris"]["normal"]
                                if "card_faces" in item
                                else None
                            )
                        )

                        if img_url:
                            st.image(img_url, use_container_width=True)

                        st.markdown(f"**{item.get('set_name')}**")
                        st.caption(
                            f"Set: {item.get('set').upper()} | #{item.get('collector_number')}"
                        )

                        btn_key = f"select_{item.get('set')}_{item.get('collector_number')}_{item.get('id')}"
                        if st.button("View Details", key=btn_key):
                            show_card_details(item)