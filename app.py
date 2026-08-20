import math
import requests
import streamlit as st

st.set_page_config(page_title="Scryfall Grid Explorer", layout="wide")
st.title("MTG Printing Visual Grid Explorer")

HEADERS = {"User-Agent": "MyMTGDataEntryApp/1.0", "Accept": "*/*"}

if "selected_card" not in st.session_state:
    st.session_state.selected_card = None


@st.cache_data(ttl=3600)
def fetch_all_printings(card_name):
    """Fetches all unique prints/sets for an exact card name."""
    url = "https://api.scryfall.com/cards/search"
    params = {"q": f'!"{card_name}"', "unique": "prints"}
    response = requests.get(url, params=params, headers=HEADERS)

    if response.status_code == 200:
        return response.json().get("data", [])
    return []


# --- SEARCH BAR & CONTROLS ---
search_col, per_page_col = st.columns([3, 1])
with search_col:
    card_input = st.text_input("Enter exact card name:", value="Sol Ring")

with per_page_col:
    # Feature 2: Dropdown to control items per page
    cards_per_page = st.selectbox(
        "Cards per page:", options=[12, 24, 48, 96], index=0
    )

if card_input:
    printings = fetch_all_printings(card_input)

    if not printings:
        st.warning(f"No printings found for '{card_input}'.")
    else:
        # --- DETAIL PANEL ---
        if st.session_state.selected_card:
            card = st.session_state.selected_card
            st.divider()

            detail_col1, detail_col2 = st.columns([1, 2])
            with detail_col1:
                # Feature 1 Fix: Use high-res 'large' or 'normal' images
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

            with detail_col2:
                st.subheader(f"{card.get('name')} [{card.get('set').upper()}]")
                st.write(f"**Set Name:** {card.get('set_name')}")
                st.write(
                    f"**Collector Number:** #{card.get('collector_number')}"
                )
                st.write(f"**Released:** {card.get('released_at')}")
                st.write(f"**Rarity:** {card.get('rarity').title()}")

                prices = card.get("prices", {})
                st.write(f"**USD Price:** ${prices.get('usd') or 'N/A'}")
                st.write(
                    f"**Foil Price:** ${prices.get('usd_foil') or 'N/A'}"
                )

                if st.button("Close Details"):
                    st.session_state.selected_card = None
                    st.rerun()

                with st.expander("View Full Raw JSON"):
                    st.json(card)

            st.divider()

        # --- PAGINATION LOGIC ---
        total_cards = len(printings)
        total_pages = math.ceil(total_cards / cards_per_page)

        pag_col1, pag_col2 = st.columns([2, 5])
        with pag_col1:
            page = st.number_input(
                f"Page (1 of {total_pages})",
                min_value=1,
                max_value=max(1, total_pages),
                value=1,
                step=1,
            )

        start_idx = (page - 1) * cards_per_page
        end_idx = start_idx + cards_per_page
        page_cards = printings[start_idx:end_idx]

        st.caption(
            f"Showing {start_idx + 1}-{min(end_idx, total_cards)} of {total_cards} printings"
        )

        # --- GRID DISPLAY (4 Columns per Row) ---
        GRID_COLUMNS = 4
        for i in range(0, len(page_cards), GRID_COLUMNS):
            cols = st.columns(GRID_COLUMNS)
            row_cards = page_cards[i : i + GRID_COLUMNS]

            for idx, item in enumerate(row_cards):
                with cols[idx]:
                    # Feature 1 Fix: Use 'normal' instead of 'small' for clear grid rendering
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
                    if st.button("Inspect", key=btn_key):
                        st.session_state.selected_card = item
                        st.rerun()