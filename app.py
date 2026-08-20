import requests
import streamlit as st

st.set_page_config(page_title="Scryfall Explorer", layout="wide")
st.title("Scryfall Card API Inspector")

# Scryfall requires a custom User-Agent header
HEADERS = {"User-Agent": "MyMTGDataEntryApp/1.0", "Accept": "*/*"}


@st.cache_data(ttl=3600)
def search_scryfall(query):
    url = "https://api.scryfall.com/cards/search"
    response = requests.get(url, params={"q": query}, headers=HEADERS)
    if response.status_code == 200:
        return response.json().get("data", [])
    return []


# Search Input
query = st.text_input("Search for a card name:", value="Sol Ring")

if query:
    cards = search_scryfall(query)

    if not cards:
        st.warning("No cards found.")
    else:
        # Selectbox to choose card printing
        card_options = {
            f"{c['name']} [{c.get('set', '').upper()}]": c for c in cards
        }
        selected_label = st.selectbox(
            "Select version:", list(card_options.keys())
        )
        card_data = card_options[selected_label]

        # Display Card Image on Left
        col1, col2 = st.columns([1, 2])

        with col1:
            if "image_uris" in card_data:
                st.image(
                    card_data["image_uris"].get("normal"),
                    use_container_width=True,
                )
            elif (
                "card_faces" in card_data
                and "image_uris" in card_data["card_faces"][0]
            ):
                st.image(
                    card_data["card_faces"][0]["image_uris"].get("normal"),
                    use_container_width=True,
                )

        # Display Raw Key/Value Data on Right
        with col2:
            st.subheader(f"Raw API Response for '{card_data.get('name')}'")

            # Option 1: Formatted Interactive JSON tree
            with st.expander("Expand interactive JSON view", expanded=False):
                st.json(card_data)

            # Option 2: Key-Value Table
            st.write("### Key / Value Pairs")
            formatted_data = []
            for key, value in card_data.items():
                formatted_data.append(
                    {"Key": key, "Type": type(value).__name__, "Value": str(value)}
                )

            st.dataframe(formatted_data, use_container_width=True, height=500)