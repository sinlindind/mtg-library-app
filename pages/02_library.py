import streamlit as st
from services.database import get_user_library, update_library_card, remove_from_library, add_card_to_library, update_card_tags
from services.scryfall import get_card_by_id, get_card_image_url

st.set_page_config(page_title="My Library", page_icon="📚", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: flex !important;}
        [data-testid="collapsedControl"] {display: flex !important;}
    </style>
""", unsafe_allow_html=True)

if "user" not in st.session_state or st.session_state.user is None:
    st.switch_page("app.py")

user = st.session_state.user
user_library = get_user_library(user["id"])
active_cards = [card for card in user_library if card.get("quantity", 0) > 0]

# Collect all unique existing tags across active cards
all_existing_tags = sorted(list({tag for card in active_cards for tag in card.get("tags", []) if tag}))

with st.sidebar:
    st.title(f"👤 {user['username']}")
    st.markdown("### Navigation")
    st.page_link("pages/01_search.py", label="Search", icon="🔍")
    st.page_link("pages/02_library.py", label="My Library", icon="📚")
    st.page_link("pages/03_wishlist.py", label="My Wishlist", icon="❤️")
    st.divider()

    st.markdown("### 🏷️ Filter by Tags")
    selected_tag_filter = st.multiselect(
        "Show cards with tags:",
        options=all_existing_tags,
        key="library_tag_filter"
    )

    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state.user = None
        st.switch_page("app.py")

# Apply sidebar tag filter
filtered_cards = active_cards
if selected_tag_filter:
    filtered_cards = [
        card for card in active_cards 
        if any(tag in card.get("tags", []) for tag in selected_tag_filter)
    ]

st.subheader(f"My Library ({len(filtered_cards)} items)")

if not filtered_cards:
    st.info("No cards found matching the criteria. Use Search to add cards or clear tag filters!")
else:
    grouped_library = {}
    for item in filtered_cards:
        sid = item.get("scryfall_id")
        if sid not in grouped_library:
            grouped_library[sid] = []
        grouped_library[sid].append(item)

    cols = st.columns(3)
    for idx, (scryfall_id, variants) in enumerate(grouped_library.items()):
        col = cols[idx % 3]
        card_data = get_card_by_id(scryfall_id) if scryfall_id else None
        tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None

        with col:
            with st.container(border=True):
                if card_data:
                    img_url = get_card_image_url(card_data, size="normal")
                    st.image(img_url, use_container_width=True)
                    if tcg_url:
                        st.markdown(f"**{card_data.get('name', 'Unknown')}** ([TCG]({tcg_url}))")
                    else:
                        st.markdown(f"**{card_data.get('name', 'Unknown')}**")
                    st.caption(f"Set: {card_data.get('set_name', 'Unknown')}")
                else:
                    st.caption("Card details unavailable")

                st.divider()

                for var in variants:
                    entry_id = var.get("id")
                    qty = var.get("quantity", 0)
                    finish = var.get("finish", "nonfoil").capitalize()
                    cond = var.get("condition", "Near Mint")
                    current_tags = var.get("tags", []) or []

                    st.markdown(f"**{qty}x** {finish} (`{cond}`)")
                    
                    # Display existing tags or empty prompt
                    if current_tags:
                        st.write(" ".join([f"`🏷️ {t}`" for t in current_tags]))

                    # Tag Editor Popover
                    with st.popover("🏷️ Edit Tags", use_container_width=True):
                        # Multiselect for choosing existing tags
                        updated_tags = st.multiselect(
                            "Select existing tags",
                            options=sorted(list(set(all_existing_tags + current_tags))),
                            default=current_tags,
                            key=f"tag_select_{entry_id}"
                        )

                        # Input to create a brand-new tag
                        new_tag_input = st.text_input(
                            "Or add a new custom tag:",
                            placeholder="e.g. Commander, Binder 1, Trade",
                            key=f"new_tag_input_{entry_id}"
                        ).strip()

                        if st.button("Save Tags", key=f"save_tags_{entry_id}", use_container_width=True):
                            final_tags = list(updated_tags)
                            
                            # Append the new typed tag if present and not a duplicate
                            if new_tag_input and new_tag_input not in final_tags:
                                final_tags.append(new_tag_input)

                            update_card_tags(entry_id, final_tags)
                            st.toast("Tags updated!", icon="✅")
                            st.rerun()

                    c_dec, c_inc = st.columns(2)
                    with c_dec:
                        if st.button("➖ 1", key=f"lib_dec_{entry_id}", use_container_width=True):
                            new_qty = qty - 1
                            if new_qty <= 0:
                                remove_from_library(entry_id)
                                st.toast("Variant removed", icon="🗑️")
                            else:
                                update_library_card(entry_id, quantity=new_qty)
                                st.toast(f"Updated quantity to {new_qty}", icon="📉")
                            st.rerun()

                    with c_inc:
                        if st.button("➕ 1", key=f"lib_inc_{entry_id}", use_container_width=True):
                            update_library_card(entry_id, quantity=qty + 1)
                            st.toast(f"Updated quantity to {qty + 1}", icon="📈")
                            st.rerun()

                card_finishes = card_data.get("finishes", ["nonfoil", "foil", "etched"]) if card_data else ["nonfoil", "foil", "etched"]
                with st.popover("➕ Add Variant", use_container_width=True):
                    new_finish = st.selectbox("Finish", card_finishes, key=f"add_fin_{scryfall_id}")
                    new_cond = st.selectbox(
                        "Condition",
                        ["Near Mint", "Lightly Played", "Moderately Played", "Heavily Played", "Damaged"],
                        key=f"add_cond_{scryfall_id}"
                    )
                    new_qty = st.number_input("Quantity", min_value=1, value=1, step=1, key=f"add_qty_{scryfall_id}")

                    if st.button("Add to Library", key=f"add_var_btn_{scryfall_id}", use_container_width=True):
                        add_card_to_library(
                            user_id=user["id"],
                            scryfall_id=scryfall_id,
                            finish=new_finish,
                            quantity=new_qty,
                            condition=new_cond
                        )
                        st.toast("Added variant!", icon="✅")
                        st.rerun()