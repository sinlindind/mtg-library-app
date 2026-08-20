import requests
import streamlit as st

st.set_page_config(page_title="Scryfall Prints Explorer", layout="wide")
st.title("Scryfall Printings Inspector")

HEADERS = {"User-Agent": "MyMTGDataEntryApp/1.0", "Accept": "*/*"}


@st.cache_data(ttl=3600)
def fetch_all_printings(card_name):
    """Fetches all unique prints/sets for an exact card name."""
    url = "https://api.scryfall.com/cards/search"
    # exact name search + unique=prints disables rollup
    params = {"q": f'!"{card_name}"', "unique": "prints"}
    response = requests.get(url, params=params, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get("data", [])
    return []


card_input = st.text_input("Enter exact card name:", value="Sol Ring")

if card_input:
    printings = fetch_all_printings(card_input)

    if not printings:
        st.warning(f"No printings found for '{card_input}'.")
    else:
        st.success(f"Found {len(printings)} printings across different sets!")

        # Create dropdown options using Set Name and Collector Number
        printing_options = {
            f"{p.get('set_name')} ({p.get('set').upper()}) #{p.get('collector_number')}": p
            for p in printings
        }

        selected_label = st.selectbox(
            "Select specific set release:", list(printing_options.keys())
        )
        selected_card = printing_options[selected_label]

        col1, col2 = st.columns([1, 2])

        with col1:
            if "image_uris" in selected_card:
                st.image(
                    selected_card["image_uris"].get("normal"),
                    use_container_width=True,
                )

        with col2:
            st.subheader(
                f"{selected_card.get('name')} — {selected_card.get('set_name')}"
            )
            st.write(f"**Set Code:** {selected_card.get('set').upper()}")
            st.write(f"**Released:** {selected_card.get('released_at')}")
            st.write(
                f"**USD Price:** ${selected_card.get('prices', {}).get('usd', 'N/A')}"
            )

            with st.expander("View Full Raw JSON for this Set Version"):
                st.json(selected_card)