import streamlit as st
import streamlit.components.v1 as components

from services.database import (
    get_user_by_username,
    get_user_library_paginated,
    get_user_wishlist_paginated,
    add_card_to_library,
    remove_from_library,
    update_library_card,
    add_to_wishlist,
    remove_from_wishlist,
    update_user_card_metadata,
    update_wishlist_metadata,
    update_card_tags
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

def scroll_to_top():
    """Scrolls parent window top to view top of results when page changes."""
    components.html(
        "<script>window.parent.scrollTo({top: 0, behavior: 'instant'});</script>",
        height=0
    )

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
            scroll_to_top()
            st.rerun()
    with p_col2:
        if st.button("◀️", key=f"{page_key}_prev_{key_suffix}", disabled=current_page == 1):
            st.session_state[page_key] -= 1
            scroll_to_top()
            st.rerun()
    with p_col3:
        st.caption(f"Page **{current_page}** of **{total_pages}** ({total_items} items total)")
    with p_col4:
        if st.button("▶️", key=f"{page_key}_next_{key_suffix}", disabled=current_page == total_pages):
            st.session_state[page_key] += 1
            scroll_to_top()
            st.rerun()
    with p_col5:
        if st.button("⏭️", key=f"{page_key}_last_{key_suffix}", disabled=current_page == total_pages):
            st.session_state[page_key] = total_pages
            scroll_to_top()
            st.rerun()

# --- DIALOG POPUP FOR MANAGING VARIANTS & TAGS ---
@st.dialog("Manage Card Inventory")
def manage_card_inventory_dialog(group, user_id):
    scryfall_id = group["scryfall_id"]
    entries = group["entries"]
    first_entry = entries[0]
    card_name = first_entry.get("card_name") or "Unknown Card"
    set_name = first_entry.get("set_name") or "Unknown Set"
    img_url = first_entry.get("image_url") or ""

    st.markdown(f"### **{card_name}**")
    st.caption(f"Set: `{set_name}`")

    st.markdown("#### **Current Copies & Tags**")
    
    # Render existing finishes, conditions, and tags
    for entry in entries:
        entry_id = entry.get("id")
        finish = entry.get("finish", "nonfoil").capitalize()
        cond = entry.get("condition", "NM")
        qty = entry.get("quantity", 1)
        current_tags = entry.get("tags") or []

        st.markdown(f"**{finish}** ({cond})")
        c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="center")
        with c1:
            new_qty = st.number_input(
                "Qty", 
                min_value=0, 
                value=int(qty), 
                key=f"dlg_qty_{entry_id}"
            )
        with c2:
            tag_input = st.text_input(
                "Tags (comma-separated)",
                value=", ".join(current_tags),
                key=f"dlg_tags_{entry_id}",
                placeholder="Commander, Foil, Trade"
            )
        with c3:
            st.write("") # Spacer
            if st.button("💾", key=f"dlg_save_{entry_id}"):
                if new_qty == 0:
                    remove_from_library(entry_id)
                    st.toast("Variant deleted", icon="🗑️")
                else:
                    parsed_tags = [t.strip() for t in tag_input.split(",") if t.strip()]
                    update_library_card(entry_id, quantity=new_qty)
                    update_card_tags(entry_id, parsed_tags)
                    st.toast("Updated variant & tags", icon="✅")
                st.rerun(scope="app")

        st.divider()

    # Add a new variant entry
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
            add_card_to_library(
                user_id=user_id,
                scryfall_id=scryfall_id,
                finish=new_finish,
                quantity=add_qty,
                condition=new_cond,
                card_name=card_name,
                set_name=set_name,
                image_url=img_url
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

        st.iframe(
            "data:text/html;charset=utf-8,"
            "<script>"
            "  const inputs = window.parent.document.querySelectorAll('input[type=\"text\"]');"
            "  if (inputs.length > 0) { inputs[0].focus(); }"
            "</script>",
            height=1
        )

        if login_submitted:
            user_record = get_user_by_username(login_username)
            if user_record:
                stored_hash, stored_salt = user_record["password_hash"].split(":")
                if verify_password(login_password, stored_hash, stored_salt):
                    st.session_state.user = user_record
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            else:
                st.error("Invalid username or password.")

# --- AUTHENTICATED VIEW (APP DASHBOARD) ---
else:
    user = st.session_state.user

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

        # Dedicated Tab-Specific Controls
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
                    options=[
                        "Name (A-Z)",
                        "Name (Z-A)",
                        "Price: Low to High",
                        "Price: High to Low",
                        "Released: Newest",
                        "Released: Oldest"
                    ],
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
                    options=[
                        "Name (A-Z)",
                        "Name (Z-A)",
                        "Quantity: High to Low",
                        "Quantity: Low to High",
                        "Set Name (A-Z)"
                    ],
                    key="library_sort_option",
                    label_visibility="collapsed",
                    on_change=lambda: st.session_state.update({"lib_page": 1})
                )
            active_query = f"{lib_query}_{lib_sort_option}"

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
                    options=[
                        "Name (A-Z)",
                        "Name (Z-A)",
                        "Price: Low to High",
                        "Price: High to Low",
                        "Set Name (A-Z)"
                    ],
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
                add_card_to_library(
                    user["id"], card_id, "nonfoil", 1, "Near Mint", 
                    float(usd) if usd != "N/A" else None, 
                    card_name=c_name, set_name=s_name, image_url=img_url
                )
                st.toast(f"Added {c_name} (Reg)", icon="✅")
                st.rerun(scope="fragment")

            if b2.button("✨ Foil", key=f"add_foil_{card_id}_{idx}"):
                add_card_to_library(
                    user["id"], card_id, "foil", 1, "Near Mint", 
                    float(usd_foil) if usd_foil != "N/A" else None,
                    card_name=c_name, set_name=s_name, image_url=img_url
                )
                st.toast(f"Added {c_name} (Foil)", icon="✨")
                st.rerun(scope="fragment")

            if b3.button("❤️", key=f"wish_{card_id}_{idx}"):
                add_to_wishlist(user["id"], card_id, card_name=c_name, set_name=s_name, image_url=img_url)
                st.toast("Added to Wishlist", icon="❤️")
                st.rerun(scope="fragment")

        st.divider()

    # --- FRAGMENT: LIBRARY ROW (AGGREGATED WITH POPUP MODAL & TAGS) ---
    @st.fragment
    def render_library_row(group):
        c_preview, c_info, c_details, c_total, c_action = st.columns([0.5, 2.5, 2.5, 1.0, 1.5], vertical_alignment="center")
        
        scryfall_id = group["scryfall_id"]
        entries = group["entries"]
        total_qty = group["total_quantity"]

        first_entry = entries[0]
        card_name = first_entry.get("card_name") or "Unknown Card"
        set_name = first_entry.get("set_name") or "Unknown Set"
        img_url = first_entry.get("image_url") or ""

        if not card_name or not img_url:
            card_data = fetch_cached_card(scryfall_id)
            if card_data:
                card_name = card_data.get("name")
                set_name = card_data.get("set_name")
                img_url = get_card_image_url(card_data, size="large") or get_card_image_url(card_data, size="normal")
                for entry in entries:
                    update_user_card_metadata(entry["id"], card_name, set_name, img_url)

        # Collect all tags across variants for row preview
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

        with c_total:
            st.markdown(f"<h3 style='text-align: right; margin: 0;'>{total_qty}x Total</h3>", unsafe_allow_html=True)

        with c_action:
            if st.button("⚙️ Manage", key=f"btn_manage_{scryfall_id}", width="stretch"):
                manage_card_inventory_dialog(group, user["id"])

        st.divider()

    # --- FRAGMENT: WISHLIST ROW ---
    @st.fragment
    def render_wishlist_row(wish_item, idx):
        c_preview, c_info, c_price, c_actions = st.columns([.4, 3.0, 1.5, 2.2])
        scryfall_id = wish_item.get("scryfall_id")

        card_data = fetch_cached_card(scryfall_id)
        if not wish_item.get("card_name") or not wish_item.get("image_url"):
            if card_data:
                c_name = card_data.get("name")
                s_name = card_data.get("set_name")
                img_url = get_card_image_url(card_data, size="large") or get_card_image_url(card_data, size="normal")
                update_wishlist_metadata(wish_item["id"], c_name, s_name, img_url)
                wish_item["card_name"] = c_name
                wish_item["set_name"] = s_name
                wish_item["image_url"] = img_url

        card_name = wish_item.get("card_name") or "Unknown Card"
        set_name = wish_item.get("set_name") or "Unknown Set"
        img_url = wish_item.get("image_url") or ""
        usd = card_data.get("prices", {}).get("usd") if card_data else "N/A"
        tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None

        with c_preview:
            if img_url:
                st.image(img_url, width="stretch")

        with c_info:
            st.markdown(f"**{card_name}** · `{set_name}`")

        with c_price:
            st.caption(f"Price: **${usd or 'N/A'}**")

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

            offset = (st.session_state.lib_page - 1) * lib_page_size
            paged_library, total_lib_items = get_user_library_paginated(
                user_id=user["id"],
                limit=lib_page_size,
                offset=offset,
                search_query=lib_query if lib_query else None,
                sort_by=lib_sort_option
            )
            total_lib_pages = max(1, (total_lib_items + lib_page_size - 1) // lib_page_size)

            if st.session_state.lib_page > total_lib_pages:
                st.session_state.lib_page = total_lib_pages

            if not paged_library:
                st.info("No matching cards in your library.")
            else:
                for group in paged_library:
                    render_library_row(group)

                # Bottom Pagination Bar
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
                sort_by=wish_sort_option
            )
            total_wish_pages = max(1, (total_wish_items + wish_page_size - 1) // wish_page_size)

            if st.session_state.wish_page > total_wish_pages:
                st.session_state.wish_page = total_wish_pages

            if not paged_wishlist:
                st.info("No matching items in your wishlist.")
            else:
                for idx, wish_item in enumerate(paged_wishlist):
                    render_wishlist_row(wish_item, idx)

                # Bottom Pagination Bar
                render_pagination_bar("wish_page", st.session_state.wish_page, total_wish_pages, total_wish_items, key_suffix="bottom")