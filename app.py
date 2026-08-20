import math
import requests
import streamlit as st

st.set_page_config(page_title="Scryfall Grid Explorer", layout="wide")
st.title("MTG Printing Visual Grid Explorer")

HEADERS = {"User-Agent": "MyMTGDataEntryApp/1.0", "Accept": "*/*"}


@st.cache_data(ttl=3600)
def fetch_all_printings(card_name):
    """Fetches all unique prints/sets for an exact card name."""
    url = "https://api.scryfall.com/cards/search"
    params = {"q": f'!"{card_name}"', "unique": "prints"}
    response = requests.get(url, params=params, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get("data", [])
    return []


# --- MODAL DIALOG FUNCTION ---
@st.dialog("Card Details", width="large")
def show_card_details(card):
    """Renders the inspect details in a pop-up window layered over the grid."""
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
        # --- PAGINATION & PER PAGE CONTROLS (SIDE BY SIDE) ---
        pag_col1, pag_col2, _ = st.columns([2, 2, 4])

        # Temporary total calculation for upper bounds
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

        # Recalculate true totals based on user's selectbox choice
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