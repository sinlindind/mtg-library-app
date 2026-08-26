import streamlit as st

from services.database import (
    get_user_by_username,
    get_user_library,
    get_user_library_paginated,
    get_user_wishlist_paginated,
    add_card_to_library,
    remove_from_library,
    update_library_card,
    add_to_wishlist,
    remove_from_wishlist,
    update_user_card_metadata,
    update_wishlist_metadata,
    update_card_tags,
    sync_user_prices_on_login
)
from services.scryfall import search_cards, get_card_by_id, get_card_image_url
from utils.auth import verify_password

st.set_page_config(page_title="MTG Hub", page_icon="🃏", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for sticky header bar, zero clipping, and native page scrolling
st.markdown("""
    <style>
        /* 1. Hide Streamlit's native top header bar */
        header[data-testid="stHeader"] {
            display: none !important;
        }

        /* 2. Hide standard sidebar and toggle control completely */
        [data-testid="stSidebar"], 
        [data-testid="collapsedControl"] { 
            display: none !important; 
        }

        /* 3. Flush Viewport Padding Reset */
        html, body, .stApp {
            overflow-x: hidden !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .stApp, section.main, .block-container {
            padding-top: 0rem !important;
            margin-top: 0rem !important;
            max-width: 100% !important;
        }

        /* Remove auto-gap on the first element in the main layout */
        div[data-testid="stMainBlockContainer"] {
            padding-top: 0rem !important;
        }

        /* 4. Sticky Header Container - Locked Flush at y=0 */
        div[data-testid="stVerticalBlock"] > div:has(div.sticky-header-marker) {
            position: sticky !important;
            top: 0 !important;
            z-index: 99999 !important;
            background-color: #0e1117 !important;
            padding-top: 0.5rem !important;
            padding-bottom: 0.75rem !important;
            margin-top: 0rem !important;
            border-bottom: 1px solid #2e303e !important;
        }

        /* 5. Standardize button heights and vertical alignment */
        div.stButton > button {
            height: 2.25rem !important;
            padding: 0 0.5rem !important;
            font-size: 0.85rem !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }

        /* 6. Standardize segmented control height */
        div[data-testid="stSegmentedControl"] {
            min-height: 2.25rem !important;
        }
    </style>
""", unsafe_allow_html=True)

# Standardized Sort Options across the whole application
SORT_OPTIONS = [
    "Name (A-Z)",
    "Name (Z-A)",
    "Price: Low to High",
    "Price: High to Low",
    "Released: Newest",
    "Released: Oldest"
]

# Initialize Session State
if "user" not in st.session_state:
    st.session_state.user = None

if "scryfall_search" not in st.session_state:
    st.session_state.scryfall_search = ""

if "card_cache" not in st.session_state:
    st.session_state.card_cache = {}

if "lib_page" not in st.session_state:
    st.session_state.lib_page = 1

if "wish_page" not in st.session_state:
    st.session_state.wish_page = 1

def fetch_cached_card(scryfall_id):
    """Retrieve card payload from session memory or query network once."""
    if scryfall_id not in st.session_state.card_cache:
        card = get_card_by_id(scryfall_id)
        if card:
            st.session_state.card_cache[scryfall_id] = card
    return st.session_state.card_cache.get(scryfall_id)

def render_pagination_bar(page_key, current_page, total_pages, total_items, key_suffix="bottom"):
    """Reusable bottom toolbar for page navigation controls."""
    p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns([1, 1, 3, 1, 1], vertical_alignment="center")
    
    with p_col1:
        if st.button("⏮️", key=f"{page_key}_first_{key_suffix}", disabled=current_page == 1):
            st.session_state[page_key] = 1
            st.rerun()
    with p_col2:
        if st.button("◀️", key=f"{page_key}_prev_{key_suffix}", disabled=current_page == 1):
            st.session_state[page_key] -= 1
            st.rerun()
    with p_col3:
        st.caption(f"Page **{current_page}** of **{total_pages}** ({total_items} items total)")
    with p_col4:
        if st.button("▶️", key=f"{page_key}_next_{key_suffix}", disabled=current_page == total_pages):
            st.session_state[page_key] += 1
            st.rerun()
    with p_col5:
        if st.button("⏭️", key=f"{page_key}_last_{key_suffix}", disabled=current_page == total_pages):
            st.session_state[page_key] = total_pages
            st.rerun()

# --- DIALOG POPUP FOR MANAGING VARIANTS & TAGS ---
@st.dialog("Manage Card Inventory")
def manage_card_inventory_dialog(group, user_id, all_existing_tags):
    scryfall_id = group["scryfall_id"]
    entries = group["entries"]
    first_entry = entries[0]
    card_name = first_entry.get("card_name") or "Unknown Card"
    set_name = first_entry.get("set_name") or "Unknown Set"

    st.markdown(f"### **{card_name}**")
    st.caption(f"Set: `{set_name}`")

    st.markdown("#### **Current Copies & Tags**")
    
    for entry in entries:
        entry_id = entry.get("id")
        finish = entry.get("finish", "nonfoil").capitalize()
        cond = entry.get("condition", "NM")
        qty = entry.get("quantity", 1)
        current_tags = entry.get("tags") or []

        st.markdown(f"**{finish}** ({cond})")
        
        new_qty = st.number_input(
            "Qty", 
            min_value=0, 
            value=int(qty), 
            key=f"dlg_qty_{entry_id}"
        )
        
        selected_existing = st.multiselect(
            "Select Existing Tags",
            options=all_existing_tags,
            default=[t for t in current_tags if t in all_existing_tags],
            key=f"dlg_tags_select_{entry_id}"
        )
        
        new_custom_tags = st.text_input(
            "Create New Tags (comma-separated)",
            value=", ".join([t for t in current_tags if t not in all_existing_tags]),
            key=f"dlg_tags_new_{entry_id}",
            placeholder="e.g. Vintage, Signed, Proxy"
        )
        
        if st.button("💾 Save Changes", key=f"dlg_save_{entry_id}"):
            if new_qty == 0:
                remove_from_library(entry_id)
                st.toast("Variant deleted", icon="🗑️")
            else:
                parsed_new = [t.strip() for t in new_custom_tags.split(",") if t.strip()]
                combined_tags = list(set(selected_existing + parsed_new))
                update_library_card(entry_id, quantity=new_qty)
                update_card_tags(entry_id, combined_tags)
                st.toast("Updated variant & tags", icon="✅")
            st.rerun(scope="app")

        st.divider()

    st.markdown("#### **Add Variant**")
    with st.form(key=f"add_variant_form_{scryfall_id}"):
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            new_finish = st.selectbox("Finish", options=["nonfoil", "foil", "etched"], key=f"add_fin_{scryfall_id}")
        with fc2:
            new_cond = st.selectbox("Condition", options=["Near Mint", "Lightly Played", "Moderately Played", "Heavily Played", "Damaged"], key=f"add_cond_{scryfall_id}")
        with fc3:
            add_qty = st.number_input("Quantity", min_value=1, value=1, key=f"add_qty_{scryfall_id}")
        
        if st.form_submit_button("➕ Add Entry", width="stretch"):
            card_data = fetch_cached_card(scryfall_id)
            price_val = 0.0
            if card_data:
                p_str = card_data.get("prices", {}).get("usd_foil" if new_finish == "foil" else "usd")
                try:
                    price_val = float(p_str) if p_str else 0.0
                except (ValueError, TypeError):
                    price_val = 0.0

            add_card_to_library(
                user_id=user_id,
                scryfall_id=scryfall_id,
                finish=new_finish,
                quantity=add_qty,
                condition=new_cond,
                card_name=card_name,
                set_name=set_name,
                image_url=first_entry.get("image_url") or "",
                current_price=price_val,
                released_at=card_data.get("released_at") if card_data else None
            )
            st.toast("Variant added successfully!", icon="✅")
            st.rerun(scope="app")

# --- UNAUTHENTICATED VIEW (LOGIN) ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🃏 MTG Library App")
        st.subheader("Login to your account")

        with st.form("login_form", clear_on_submit=False):
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            login_submitted = st.form_submit_button("Login", width="stretch")

        if login_submitted:
            user_record = get_user_by_username(login_username)
            if user_record:
                stored_hash, stored_salt = user_record["password_hash"].split(":")
                if verify_password(login_password, stored_hash, stored_salt):
                    st.session_state.user = user_record
                    sync_user_prices_on_login(user_record["id"], fetch_cached_card)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            else:
                st.error("Invalid username or password.")

# --- AUTHENTICATED VIEW (APP DASHBOARD) ---
else:
    user = st.session_state.user

    all_lib_raw = get_user_library(user["id"])
    existing_tags = set()
    for entry in all_lib_raw:
        if entry.get("tags"):
            existing_tags.update(entry.get("tags"))
    
    sorted_tags = sorted(list(existing_tags))

    # --- STICKY TOP HEADER CONTAINER ---
    with st.container():
        st.markdown('<div class="sticky-header-marker"></div>', unsafe_allow_html=True)
        col_brand, col_nav, col_user = st.columns([1.2, 3.8, 1.2], vertical_alignment="center")

        with col_brand:
            st.markdown("### 🃏 **MTG Hub**")

        with col_nav:
            current_tab = st.segmented_control(
                label="Navigation",
                options=["🔍 Search", "📚 Library", "❤️ Wishlist"],
                default="🔍 Search",
                key="active_tab",
                label_visibility="collapsed"
            )

        with col_user:
            u_col, lg_col = st.columns([1.5, 1], vertical_alignment="center")
            u_col.caption(f"👤 **{user['username']}**")
            if lg_col.button("Logout", key="top_logout_btn"):
                st.session_state.clear()
                st.rerun()

        selected_tags = []
        
        if current_tab == "🔍 Search":
            search_col, sort_col = st.columns([3.5, 1.5], vertical_alignment="center")
            with search_col:
                search_query = st.text_input(
                    "Scryfall Search",
                    value=st.session_state.get("scryfall_search", ""),
                    placeholder="Search Scryfall... e.g. Sol Ring, Black Lotus",
                    key="scryfall_search_input",
                    label_visibility="collapsed"
                )
            with sort_col:
                sort_option = st.selectbox(
                    "Sort Search Results",
                    options=SORT_OPTIONS,
                    key="search_sort_option",
                    label_visibility="collapsed"
                )
            st.session_state["scryfall_search"] = search_query
            active_query = f"{search_query}_{sort_option}"

        elif current_tab == "📚 Library":
            search_col, sort_col = st.columns([3.5, 1.5], vertical_alignment="center")
            with search_col:
                lib_query = st.text_input(
                    "Filter Library",
                    placeholder="Filter Library by card name or set...",
                    key="library_search_input",
                    label_visibility="collapsed",
                    on_change=lambda: st.session_state.update({"lib_page": 1})
                ).strip().lower()
            with sort_col:
                lib_sort_option = st.selectbox(
                    "Sort Library",
                    options=SORT_OPTIONS,
                    key="library_sort_option",
                    label_visibility="collapsed",
                    on_change=lambda: st.session_state.update({"lib_page": 1})
                )

            if sorted_tags:
                with st.expander("🏷️ **Filter by Tags**", expanded=False):
                    tag_cols = st.columns(min(len(sorted_tags), 6))
                    for i, tag in enumerate(sorted_tags):
                        col_idx = i % min(len(sorted_tags), 6)
                        with tag_cols[col_idx]:
                            if st.checkbox(tag, key=f"tag_cb_{tag}", on_change=lambda: st.session_state.update({"lib_page": 1})):
                                selected_tags.append(tag)

            active_query = f"{lib_query}_{'_'.join(selected_tags)}_{lib_sort_option}"

        elif current_tab == "❤️ Wishlist":
            search_col, sort_col = st.columns([3.5, 1.5], vertical_alignment="center")
            with search_col:
                wish_query = st.text_input(
                    "Filter Wishlist",
                    placeholder="Filter Wishlist by card name or set...",
                    key="wishlist_search_input",
                    label_visibility="collapsed",
                    on_change=lambda: st.session_state.update({"wish_page": 1})
                ).strip().lower()
            with sort_col:
                wish_sort_option = st.selectbox(
                    "Sort Wishlist",
                    options=SORT_OPTIONS,
                    key="wishlist_sort_option",
                    label_visibility="collapsed",
                    on_change=lambda: st.session_state.update({"wish_page": 1})
                )
            active_query = f"{wish_query}_{wish_sort_option}"

    # --- FRAGMENT: SEARCH ROW ---
    @st.fragment
    def render_search_row(card, idx):
        c_preview, c_info, c_price, c_actions = st.columns([1.8, 3.0, 1.5, 2.2])
        img_url = get_card_image_url(card, size="large") or get_card_image_url(card, size="normal")
        usd = card.get("prices", {}).get("usd") or "N/A"
        usd_foil = card.get("prices", {}).get("usd_foil") or "N/A"
        card_id = card["id"]
        c_name = card.get("name")
        s_name = card.get("set_name")
        rel_at = card.get("released_at")

        st.session_state.card_cache[card_id] = card

        with c_preview:
            if img_url:
                st.image(img_url, width="stretch")

        with c_info:
            st.markdown(f"**{c_name}** · `{s_name}`")

        with c_price:
            st.caption(f"Reg: **${usd}** | Foil: **${usd_foil}**")

        with c_actions:
            b1, b2, b3 = st.columns(3)
            if b1.button("➕ Reg", key=f"add_reg_{card_id}_{idx}"):
                price_val = float(usd) if usd != "N/A" else 0.0
                add_card_to_library(
                    user["id"], card_id, "nonfoil", 1, "Near Mint", 
                    purchase_price=price_val, 
                    card_name=c_name, set_name=s_name, image_url=img_url,
                    current_price=price_val, released_at=rel_at
                )
                st.toast(f"Added {c_name} (Reg)", icon="✅")
                st.rerun(scope="fragment")

            if b2.button("✨ Foil", key=f"add_foil_{card_id}_{idx}"):
                price_val = float(usd_foil) if usd_foil != "N/A" else 0.0
                add_card_to_library(
                    user["id"], card_id, "foil", 1, "Near Mint", 
                    purchase_price=price_val,
                    card_name=c_name, set_name=s_name, image_url=img_url,
                    current_price=price_val, released_at=rel_at
                )
                st.toast(f"Added {c_name} (Foil)", icon="✨")
                st.rerun(scope="fragment")

            if b3.button("❤️", key=f"wish_{card_id}_{idx}"):
                price_val = float(usd) if usd != "N/A" else 0.0
                add_to_wishlist(
                    user["id"], card_id, card_name=c_name, set_name=s_name, image_url=img_url,
                    current_price=price_val, released_at=rel_at
                )
                st.toast("Added to Wishlist", icon="❤️")
                st.rerun(scope="fragment")

        st.divider()

    # --- FRAGMENT: LIBRARY ROW ---
    @st.fragment
    def render_library_row(group, sorted_tags):
        c_preview, c_info, c_details, c_price_qty, c_action = st.columns([0.5, 2.5, 2.0, 1.5, 1.5], vertical_alignment="center")
        
        scryfall_id = group["scryfall_id"]
        entries = group["entries"]
        total_qty = group["total_quantity"]

        first_entry = entries[0]
        card_name = first_entry.get("card_name") or "Unknown Card"
        set_name = first_entry.get("set_name") or "Unknown Set"
        img_url = first_entry.get("image_url") or ""
        unit_price = first_entry.get("current_price")

        if unit_price is None or not card_name or not img_url:
            card_data = fetch_cached_card(scryfall_id)
            if card_data:
                card_name = card_data.get("name")
                set_name = card_data.get("set_name")
                img_url = get_card_image_url(card_data, size="large") or get_card_image_url(card_data, size="normal")
                price_val = card_data.get("prices", {}).get("usd")
                try:
                    unit_price = float(price_val) if price_val else 0.0
                except (ValueError, TypeError):
                    unit_price = 0.0
                for entry in entries:
                    update_user_card_metadata(entry["id"], card_name, set_name, img_url, current_price=unit_price, released_at=card_data.get("released_at"))

        all_tags = set()
        for e in entries:
            if e.get("tags"):
                all_tags.update(e.get("tags"))

        with c_preview:
            if img_url:
                st.image(img_url, width="stretch")

        with c_info:
            st.markdown(f"**{card_name}** · `{set_name}`")

        with c_details:
            variant_str = ", ".join([
                f"{e.get('quantity', 1)}x {e.get('finish', 'nonfoil').capitalize()} ({e.get('condition', 'NM')})"
                for e in entries
            ])
            st.caption(variant_str)
            if all_tags:
                tags_formatted = " ".join([f"`{t}`" for t in sorted(all_tags)])
                st.caption(f"🏷️ {tags_formatted}")

        with c_price_qty:
            price_display = f"${unit_price:.2f}" if unit_price is not None else "N/A"
            st.markdown(f"<p style='text-align: right; margin: 0;'>Price: <b>{price_display}</b></p>", unsafe_allow_html=True)
            st.markdown(f"<h3 style='text-align: right; margin: 0;'>{total_qty}x Total</h3>", unsafe_allow_html=True)

        with c_action:
            if st.button("⚙️ Manage", key=f"btn_manage_{scryfall_id}", width="stretch"):
                manage_card_inventory_dialog(group, user["id"], sorted_tags)

        st.divider()

    # --- FRAGMENT: WISHLIST ROW ---
    @st.fragment
    def render_wishlist_row(wish_item, idx):
        c_preview, c_info, c_price, c_actions = st.columns([.4, 3.0, 1.5, 2.2], vertical_alignment="center")
        scryfall_id = wish_item.get("scryfall_id")

        unit_price = wish_item.get("current_price")
        card_data = fetch_cached_card(scryfall_id)

        if unit_price is None or not wish_item.get("card_name") or not wish_item.get("image_url"):
            if card_data:
                c_name = card_data.get("name")
                s_name = card_data.get("set_name")
                img_url = get_card_image_url(card_data, size="large") or get_card_image_url(card_data, size="normal")
                price_val = card_data.get("prices", {}).get("usd")
                try:
                    unit_price = float(price_val) if price_val else 0.0
                except (ValueError, TypeError):
                    unit_price = 0.0
                update_wishlist_metadata(wish_item["id"], c_name, s_name, img_url, current_price=unit_price, released_at=card_data.get("released_at"))
                wish_item["card_name"] = c_name
                wish_item["set_name"] = s_name
                wish_item["image_url"] = img_url

        card_name = wish_item.get("card_name") or "Unknown Card"
        set_name = wish_item.get("set_name") or "Unknown Set"
        img_url = wish_item.get("image_url") or ""
        tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None

        with c_preview:
            if img_url:
                st.image(img_url, width="stretch")

        with c_info:
            st.markdown(f"**{card_name}** · `{set_name}`")

        with c_price:
            price_display = f"${unit_price:.2f}" if unit_price is not None else "N/A"
            st.markdown(f"Price: **{price_display}**")

        with c_actions:
            b_tcg, b_rem = st.columns(2)
            with b_tcg:
                if tcg_url:
                    st.link_button("🛒 TCG", tcg_url, width="stretch")
            with b_rem:
                if st.button("❌ Remove", key=f"rem_w_{scryfall_id}_{idx}", width="stretch"):
                    remove_from_wishlist(user["id"], scryfall_id)
                    st.toast("Removed from Wishlist", icon="🗑️")
                    st.rerun(scope="app")

        st.divider()

    # --- DYNAMICALLY KEYED CONTENT CONTAINER ---
    container_key = f"content_{current_tab}_{active_query}"

    with st.container(border=False, key=container_key):
        if current_tab == "🔍 Search":
            if search_query:
                results = search_cards(search_query)

                def get_usd_price(card):
                    val = card.get("prices", {}).get("usd")
                    try:
                        return float(val) if val else 0.0
                    except (ValueError, TypeError):
                        return 0.0

                if sort_option == "Name (A-Z)":
                    results = sorted(results, key=lambda c: c.get("name", "").lower())
                elif sort_option == "Name (Z-A)":
                    results = sorted(results, key=lambda c: c.get("name", "").lower(), reverse=True)
                elif sort_option == "Price: Low to High":
                    results = sorted(results, key=get_usd_price)
                elif sort_option == "Price: High to Low":
                    results = sorted(results, key=get_usd_price, reverse=True)
                elif sort_option == "Released: Newest":
                    results = sorted(results, key=lambda c: c.get("released_at", ""), reverse=True)
                elif sort_option == "Released: Oldest":
                    results = sorted(results, key=lambda c: c.get("released_at", ""))

                st.caption(f"Found **{len(results)}** printings for `{search_query}` (Sorted by: {sort_option})")
                for idx, card in enumerate(results):
                    render_search_row(card, idx)
            else:
                st.info("Type a card name in the search bar above to query Scryfall.")

        elif current_tab == "📚 Library":
            lib_page_size = st.selectbox(
                "Per Page", 
                options=[25, 50, 100], 
                index=0, 
                key="lib_page_size_select",
                on_change=lambda: st.session_state.update({"lib_page": 1})
            )

            paged_library, total_lib_items = get_user_library_paginated(
                user_id=user["id"],
                limit=10000 if selected_tags else lib_page_size,
                offset=0 if selected_tags else (st.session_state.lib_page - 1) * lib_page_size,
                search_query=lib_query if lib_query else None,
                sort_by=lib_sort_option,
                fetch_cached_card_fn=fetch_cached_card
            )

            if selected_tags and paged_library:
                filtered = []
                for group in paged_library:
                    group_tags = set()
                    for entry in group.get("entries", []):
                        if entry.get("tags"):
                            group_tags.update(entry.get("tags"))
                    
                    if any(tag in group_tags for tag in selected_tags):
                        filtered.append(group)
                
                total_lib_items = len(filtered)
                offset = (st.session_state.lib_page - 1) * lib_page_size
                paged_library = filtered[offset:offset + lib_page_size]

            total_lib_pages = max(1, (total_lib_items + lib_page_size - 1) // lib_page_size)

            if st.session_state.lib_page > total_lib_pages:
                st.session_state.lib_page = total_lib_pages

            if not paged_library:
                st.info("No matching cards in your library.")
            else:
                for group in paged_library:
                    render_library_row(group, sorted_tags)

                render_pagination_bar("lib_page", st.session_state.lib_page, total_lib_pages, total_lib_items, key_suffix="bottom")

        elif current_tab == "❤️ Wishlist":
            wish_page_size = st.selectbox(
                "Per Page", 
                options=[25, 50, 100], 
                index=0, 
                key="wish_page_size_select",
                on_change=lambda: st.session_state.update({"wish_page": 1})
            )

            offset = (st.session_state.wish_page - 1) * wish_page_size
            paged_wishlist, total_wish_items = get_user_wishlist_paginated(
                user_id=user["id"],
                limit=wish_page_size,
                offset=offset,
                search_query=wish_query if wish_query else None,
                sort_by=wish_sort_option,
                fetch_cached_card_fn=fetch_cached_card
            )
            total_wish_pages = max(1, (total_wish_items + wish_page_size - 1) // wish_page_size)

            if st.session_state.wish_page > total_wish_pages:
                st.session_state.wish_page = total_wish_pages

            if not paged_wishlist:
                st.info("No matching items in your wishlist.")
            else:
                for idx, wish_item in enumerate(paged_wishlist):
                    render_wishlist_row(wish_item, idx)

                render_pagination_bar("wish_page", st.session_state.wish_page, total_wish_pages, total_wish_items, key_suffix="bottom")