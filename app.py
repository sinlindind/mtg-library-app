import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MTG Data Entry", layout="wide")
st.title("Magic: The Gathering Collection Logger")

# Scryfall requires a custom User-Agent header
HEADERS = {"User-Agent": "MyMTGDataEntryApp/1.0", "Accept": "*/*"}


@st.cache_data(ttl=3600)
def search_scryfall(query):
    """Fetch matching cards from Scryfall API."""
    url = "https://api.scryfall.com/cards/search"
    response = requests.get(url, params={"q": query}, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("data", [])
    return []


# --- SEARCH SECTION ---
query = st.text_input("Search for a card by name:", value="Sol Ring")

if query:
    cards = search_scryfall(query)

    if not cards:
        st.warning("No cards found.")
    else:
        # Create a dropdown mapping "Card Name (Set Code)" to the card data object
        card_options = {
            f"{c['name']} [{c.get('set', '').upper()}]": c for c in cards
        }
        selected_label = st.selectbox("Select card version:", list(card_options.keys()))
        card = card_options[selected_label]

        col1, col2 = st.columns([1, 2])

        with col1:
            # Handle standard single-faced and double-faced card images
            if "image_uris" in card:
                img_url = card["image_uris"].get("normal")
            elif "card_faces" in card and "image_uris" in card["card_faces"][0]:
                img_url = card["card_faces"][0]["image_uris"].get("normal")
            else:
                img_url = None

            if img_url:
                st.image(img_url, use_container_width=True)

        with col2:
            st.subheader(card.get("name"))
            st.write(f"**Type:** {card.get('type_line', 'N/A')}")
            st.write(f"**Set:** {card.get('set_name')} ({card.get('set', '').upper()})")

            # Prices
            prices = card.get("prices", {})
            usd_price = prices.get("usd") or "N/A"
            st.write(f"**Market Price (USD):** ${usd_price}")

            st.divider()

            # --- DATA ENTRY FORM ---
            with st.form("add_card_form", clear_on_submit=True):
                st.markdown("### Log to Collection")
                quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
                condition = st.selectbox(
                    "Condition",
                    ["Near Mint", "Lightly Played", "Moderately Played", "Heavily Played", "Damaged"],
                )
                is_foil = st.checkbox("Foil")
                notes = st.text_input("Notes")

                submit = st.form_submit_button("Save to Collection")

            if submit:
                entry = {
                    "Card Name": card.get("name"),
                    "Set": card.get("set", "").upper(),
                    "Collector Number": card.get("collector_number"),
                    "Quantity": quantity,
                    "Condition": condition,
                    "Foil": is_foil,
                    "Est Price (USD)": usd_price,
                    "Notes": notes,
                }

                file_path = "mtg_collection.csv"
                df_new = pd.DataFrame([entry])

                if not os.path.isfile(file_path):
                    df_new.to_csv(file_path, index=False)
                else:
                    df_new.to_csv(file_path, mode="a", header=False, index=False)

                st.success(f"Added {quantity}x {card.get('name')} to collection!")

# --- DISPLAY LOGGED ENTRIES ---
st.divider()
st.subheader("Your Logged Cards")
if os.path.isfile("mtg_collection.csv"):
    df = pd.read_csv("mtg_collection.csv")
    st.dataframe(df, use_container_width=True)
else:
    st.info("No saved cards yet.")