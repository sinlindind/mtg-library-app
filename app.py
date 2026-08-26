import streamlit as str_lit

from services.database import (
    add_card_to_library,
    add_to_wishlist,
    get_user_by_username,
    get_user_library,
    get_user_library_paginated,
    get_user_wishlist_paginated,
    remove_from_library,
    remove_from_wishlist,
    update_card_tags,
    update_library_card,
)
from services.scryfall import get_card_by_id, get_card_image_url, search_cards
from utils.auth import verify_password

str_lit.set_page_config(
    page_title="MTG Hub",
    page_icon="🃏",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for layout and header
str_lit.markdown(
    """
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
        html, body, .stApp { overflow-x: hidden !important; margin: 0 !important; padding: 0 !important; }
        .stApp, section.main, .block-container { padding-top: 0rem !important; margin-top: 0rem !important; max-width: 100% !important; }
        div[data-testid="stMainBlockContainer"] { padding-top: 0rem !important; }
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
        div.stButton > button { height: 2.25rem !important; padding: 0 0.5rem !important; font-size: 0.85rem !important; margin-top: 0 !important; margin-bottom: 0 !important; }
        div[data-testid="stSegmentedControl"] { min-height: 2.25rem !important; }
    </style>
""",
    unsafe_allow_html=True,
)

SEARCH_SORT_OPTIONS = [
    "Name (A-Z)",
    "Name (Z-A)",
    "Price: Low to High",
    "Price: High to Low",
    "Released: Newest",
    "Released: Oldest",
]

SIMPLE_SORT_OPTIONS = ["Name (A-Z)", "Name (Z-A)"]

# Initialize Session State
if "user" not in str_lit.session_state:
    str_lit.session_state.user = None

if "scryfall_search" not in str_lit.session_state:
    str_lit.session_state.scryfall_search = ""

if "card_cache" not in str_lit.session_state:
    str_lit.session_state.card_cache = {}

if "lib_page" not in str_lit.session_state:
    str_lit.session_state.lib_page = 1

if "wish_page" not in str_lit.session_state:
    str_lit.session_state.wish_page = 1


def fetch_cached_card(scryfall_id):
    if scryfall_id not in str_lit.session_state.card_cache:
        card = get_card_by_id(scryfall_id)
        if card:
            str_lit.session_state.card_cache[scryfall_id] = card
    return str_lit.session_state.card_cache.get(scryfall_id)


def render_pagination_bar(page_key, current_page, total_pages, total_items, key_suffix="bottom"):
    p_col1, p_col2, p_col3, p_col4, p_col5 = str_lit.columns([1, 1, 3, 1, 1], vertical_alignment="center")
    with p_col1:
        if str_lit.button("⏮️", key=f"{page_key}_first_{key_suffix}", disabled=current_page == 1):
            str_lit.session_state[page_key] = 1
            str_lit.rerun()
    with p_col2:
        if str_lit.button("◀️", key=f"{page_key}_prev_{key_suffix}", disabled=current_page == 1):
            str_lit.session_state[page_key] -= 1
            str_lit.rerun()
    with p_col3:
        str_lit.caption(f"Page **{current_page}** of **{total_pages}** ({total_items} items total)")
    with p_col4:
        if str_lit.button("▶️", key=f"{page_key}_next_{key_suffix}", disabled=current_page == total_pages):
            str_lit.session_state[page_key] += 1
            str_lit.rerun()
    with p_col5:
        if str_lit.button("⏭️", key=f"{page_key}_last_{key_suffix}", disabled=current_page == total_pages):
            str_lit.session_state[page_key] = total_pages
            str_lit.rerun()


# --- DIALOG FOR MANAGING LIBRARY QUANTITY & TAGS ---
@str_lit.dialog("Manage Card Quantity & Tags")
def manage_card_dialog(item, user_id, all_existing_tags):
    entry_id = item.get("id")
    card_name = item.get("card_name") or "Unknown Card"
    set_name = item.get("set_name") or "Unknown Set"
    reg_qty = item.get("reg_quantity", 0)
    foil_qty = item.get("foil_quantity", 0)
    current_tags = item.get("tags") or []

    str_lit.markdown(f"### **{card_name}**")
    str_lit.caption(f"Set: `{set_name}`")

    col_q1, col_q2 = str_lit.columns(2)
    with col_q1:
        new_reg_qty = str_lit.number_input("Regular Qty", min_value=0, value=int(reg_qty), key=f"dlg_reg_{entry_id}")
    with col_q2:
        new_foil_qty = str_lit.number_input("Foil Qty", min_value=0, value=int(foil_qty), key=f"dlg_foil_{entry_id}")

    selected_existing = str_lit.multiselect(
        "Select Existing Tags",
        options=all_existing_tags,
        default=[t for t in current_tags if t in all_existing_tags],
        key=f"dlg_tags_select_{entry_id}",
    )

    new_custom_tags = str_lit.text_input(
        "Create New Tags (comma-separated)",
        value=", ".join([t for t in current_tags if t not in all_existing_tags]),
        key=f"dlg_tags_new_{entry_id}",
        placeholder="e.g. Commander, Foil, Trade",
    )

    if str_lit.button("💾 Save Changes", key=f"dlg_save_{entry_id}"):
        if new_reg_qty == 0 and new_foil_qty == 0:
            remove_from_library(entry_id)
            str_lit.toast("Card removed from library", icon="🗑️")
        else:
            parsed_new = [t.strip() for t in new_custom_tags.split(",") if t.strip()]
            combined_tags = list(set(selected_existing + parsed_new))
            update_library_card(entry_id, reg_quantity=new_reg_qty, foil_quantity=new_foil_qty)
            update_card_tags(entry_id, combined_tags)
            str_lit.toast("Updated quantity & tags", icon="✅")
        str_lit.rerun(scope="app")


# --- UNAUTHENTICATED VIEW (LOGIN) ---
if str_lit.session_state.user is None:
    col1, col2, col3 = str_lit.columns([1, 2, 1])
    with col2:
        str_lit.title("🃏 MTG Library App")
        str_lit.subheader("Login to your account")

        with str_lit.form("login_form", clear_on_submit=False):
            login_username = str_lit.text_input("Username", key="login_user")
            login_password = str_lit.text_input("Password", type="password", key="login_pass")
            login_submitted = str_lit.form_submit_button("Login", width="stretch")

        if login_submitted:
            user_record = get_user_by_username(login_username)
            if user_record:
                stored_hash, stored_salt = user_record["password_hash"].split(":")
                if verify_password(login_password, stored_hash, stored_salt):
                    str_lit.session_state.user = user_record
                    str_lit.rerun()
                else:
                    str_lit.error("Invalid username or password.")
            else:
                str_lit.error("Invalid username or password.")

# --- AUTHENTICATED VIEW (APP DASHBOARD) ---
else:
    user = str_lit.session_state.user

    all_lib_raw = get_user_library(user["id"])
    existing_tags = set()
    library_qty_map = {}
    for entry in all_lib_raw:
        if entry.get("tags"):
            existing_tags.update(entry.get("tags"))
        sid = entry.get("scryfall_id")
        reg = entry.get("reg_quantity", 0)
        foil = entry.get("foil_quantity", 0)
        if sid not in library_qty_map:
            library_qty_map[sid] = {"reg": 0, "foil": 0}
        library_qty_map[sid]["reg"] += reg
        library_qty_map[sid]["foil"] += foil

    sorted_tags = sorted(list(existing_tags))

    # --- STICKY TOP HEADER CONTAINER ---
    with str_lit.container():
        str_lit.markdown('<div class="sticky-header-marker"></div>', unsafe_allow_html=True)
        col_brand, col_nav, col_user = str_lit.columns([1.2, 3.8, 1.2], vertical_alignment="center")

        with col_brand:
            str_lit.markdown("### 🃏 **MTG Hub**")

        with col_nav:
            current_tab = str_lit.segmented_control(
                label="Navigation",
                options=["🔍 Search", "📚 Library", "❤️ Wishlist"],
                default="🔍 Search",
                key="active_tab",
                label_visibility="collapsed",
            )

        with col_user:
            u_col, lg_col = str_lit.columns([1.5, 1], vertical_alignment="center")
            u_col.caption(f"👤 **{user['username']}**")
            if lg_col.button("Logout", key="top_logout_btn"):
                str_lit.session_state.clear()
                str_lit.rerun()

        selected_tags = []

        if current_tab == "🔍 Search":
            search_col, sort_col = str_lit.columns([3.5, 1.5], vertical_alignment="center")
            with search_col:
                search_query = str_lit.text_input(
                    "Scryfall Search",
                    value=str_lit.session_state.get("scryfall_search", ""),
                    placeholder="Search Scryfall... e.g. Sol Ring, Black Lotus",
                    key="scryfall_search_input",
                    label_visibility="collapsed",
                )
            with sort_col:
                sort_option = str_lit.selectbox(
                    "Sort Search Results",
                    options=SEARCH_SORT_OPTIONS,
                    key="search_sort_option",
                    label_visibility="collapsed",
                )
            str_lit.session_state["scryfall_search"] = search_query
            active_query = f"{search_query}_{sort_option}"

        elif current_tab == "📚 Library":
            search_col, sort_col = str_lit.columns([3.5, 1.5], vertical_alignment="center")
            with search_col:
                lib_query = str_lit.text_input(
                    "Filter Library",
                    placeholder="Filter Library by card name or set...",
                    key="library_search_input",
                    label_visibility="collapsed",
                    on_change=lambda: str_lit.session_state.update({"lib_page": 1}),
                ).strip().lower()
            with sort_col:
                lib_sort_option = str_lit.selectbox(
                    "Sort Library",
                    options=SIMPLE_SORT_OPTIONS,
                    key="library_sort_option",
                    label_visibility="collapsed",
                    on_change=lambda: str_lit.session_state.update({"lib_page": 1}),
                )

            if sorted_tags:
                with str_lit.expander("🏷️ **Filter by Tags**", expanded=False):
                    tag_cols = str_lit.columns(min(len(sorted_tags), 6))
                    for i, tag in enumerate(sorted_tags):
                        col_idx = i % min(len(sorted_tags), 6)
                        with tag_cols[col_idx]:
                            if str_lit.checkbox(
                                tag,
                                key=f"tag_cb_{tag}",
                                on_change=lambda: str_lit.session_state.update({"lib_page": 1}),
                            ):
                                selected_tags.append(tag)

            active_query = f"{lib_query}_{'_'.join(selected_tags)}_{lib_sort_option}"

        elif current_tab == "❤️ Wishlist":
            search_col, sort_col = str_lit.columns([3.5, 1.5], vertical_alignment="center")
            with search_col:
                wish_query = str_lit.text_input(
                    "Filter Wishlist",
                    placeholder="Filter Wishlist by card name or set...",
                    key="wishlist_search_input",
                    label_visibility="collapsed",
                    on_change=lambda: str_lit.session_state.update({"wish_page": 1}),
                ).strip().lower()
            with sort_col:
                wish_sort_option = str_lit.selectbox(
                    "Sort Wishlist",
                    options=SIMPLE_SORT_OPTIONS,
                    key="wishlist_sort_option",
                    label_visibility="collapsed",
                    on_change=lambda: str_lit.session_state.update({"wish_page": 1}),
                )
            active_query = f"{wish_query}_{wish_sort_option}"

    # --- FRAGMENT: SEARCH ROW ---
    @str_lit.fragment
    def render_search_row(card, idx, library_qty_map):
        c_preview, c_info, c_price, c_actions = str_lit.columns([1.5, 3.0, 1.5, 3.0])
        img_url = get_card_image_url(card, size="large") or get_card_image_url(card, size="normal")
        usd = card.get("prices", {}).get("usd") or "N/A"
        usd_foil = card.get("prices", {}).get("usd_foil") or "N/A"
        card_id = card["id"]
        c_name = card.get("name")
        s_name = card.get("set_name")

        owned_dict = library_qty_map.get(card_id, {"reg": 0, "foil": 0})
        owned_reg = owned_dict["reg"]
        owned_foil = owned_dict["foil"]
        str_lit.session_state.card_cache[card_id] = card

        with c_preview:
            if img_url:
                str_lit.image(img_url, width="stretch")

        with c_info:
            str_lit.markdown(f"**{c_name}** · `{s_name}`")
            if owned_reg > 0 or owned_foil > 0:
                str_lit.markdown(f"📦 Library: **{owned_reg}x** Reg | **{owned_foil}x** Foil")
            else:
                str_lit.caption("Not in library")

        with c_price:
            str_lit.caption(f"Reg: **${usd}** | Foil: **${usd_foil}**")

        with c_actions:
            b1, b2, b3 = str_lit.columns(3)
            if b1.button("➕ Reg", key=f"add_reg_{card_id}_{idx}"):
                add_card_to_library(
                    user_id=user["id"],
                    scryfall_id=card_id,
                    reg_quantity=1,
                    foil_quantity=0,
                    card_name=c_name,
                    set_name=s_name,
                    image_url=img_url,
                )
                str_lit.toast(f"Added {c_name} (Reg) to Library", icon="✅")
                str_lit.rerun(scope="app")

            if b2.button("✨ Foil", key=f"add_foil_{card_id}_{idx}"):
                add_card_to_library(
                    user_id=user["id"],
                    scryfall_id=card_id,
                    reg_quantity=0,
                    foil_quantity=1,
                    card_name=c_name,
                    set_name=s_name,
                    image_url=img_url,
                )
                str_lit.toast(f"Added {c_name} (Foil) to Library", icon="✨")
                str_lit.rerun(scope="app")

            if b3.button("❤️ Wish", key=f"add_wish_{card_id}_{idx}"):
                add_to_wishlist(
                    user_id=user["id"],
                    scryfall_id=card_id,
                    card_name=c_name,
                    set_name=s_name,
                    image_url=img_url,
                )
                str_lit.toast(f"Added {c_name} to Wishlist", icon="❤️")
                str_lit.rerun(scope="fragment")

        str_lit.divider()

    # --- FRAGMENT: LIBRARY ROW ---
    @str_lit.fragment
    def render_library_row(item, sorted_tags):
        c_preview, c_info, c_details, c_qty, c_action = str_lit.columns(
            [0.8, 3.0, 2.0, 1.5, 1.5], vertical_alignment="center"
        )

        scryfall_id = item["scryfall_id"]
        card_name = item.get("card_name") or "Unknown Card"
        set_name = item.get("set_name") or "Unknown Set"
        img_url = item.get("image_url") or ""
        reg_qty = item.get("reg_quantity", 0)
        foil_qty = item.get("foil_quantity", 0)
        tags = item.get("tags") or []

        with c_preview:
            if img_url:
                str_lit.image(img_url, width="stretch")

        with c_info:
            str_lit.markdown(f"**{card_name}** · `{set_name}`")

        with c_details:
            if tags:
                tags_formatted = " ".join([f"`{t}`" for t in sorted(tags)])
                str_lit.caption(f"🏷️ {tags_formatted}")

        with c_qty:
            str_lit.markdown(
                f"<div style='text-align: right;'><b>Reg:</b> {reg_qty}x | <b>Foil:</b> {foil_qty}x</div>",
                unsafe_allow_html=True,
            )

        with c_action:
            if str_lit.button("⚙️ Manage", key=f"btn_manage_{scryfall_id}", width="stretch"):
                manage_card_dialog(item, user["id"], sorted_tags)

        str_lit.divider()

    # --- FRAGMENT: WISHLIST ROW ---
    @str_lit.fragment
    def render_wishlist_row(wish_item, idx):
        c_preview, c_info, c_actions = str_lit.columns([0.8, 4.5, 2.2], vertical_alignment="center")
        scryfall_id = wish_item.get("scryfall_id")
        card_name = wish_item.get("card_name") or "Unknown Card"
        set_name = wish_item.get("set_name") or "Unknown Set"
        img_url = wish_item.get("image_url") or ""

        card_data = fetch_cached_card(scryfall_id)
        tcg_url = card_data.get("purchase_uris", {}).get("tcgplayer") if card_data else None

        with c_preview:
            if img_url:
                str_lit.image(img_url, width="stretch")

        with c_info:
            str_lit.markdown(f"**{card_name}** · `{set_name}`")

        with c_actions:
            b_tcg, b_rem = str_lit.columns(2)
            with b_tcg:
                if tcg_url:
                    str_lit.link_button("🛒 TCG", tcg_url, width="stretch")
            with b_rem:
                if str_lit.button("❌ Remove", key=f"rem_w_{scryfall_id}_{idx}", width="stretch"):
                    remove_from_wishlist(user["id"], scryfall_id)
                    str_lit.toast("Removed from Wishlist", icon="🗑️")
                    str_lit.rerun(scope="app")

        str_lit.divider()

    # --- DYNAMICALLY KEYED CONTENT CONTAINER ---
    container_key = f"content_{current_tab}_{active_query}"

    with str_lit.container(border=False, key=container_key):
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

                str_lit.caption(f"Found **{len(results)}** printings for `{search_query}` (Sorted by: {sort_option})")
                for idx, card in enumerate(results):
                    render_search_row(card, idx, library_qty_map)
            else:
                str_lit.info("Type a card name in the search bar above to query Scryfall.")

        elif current_tab == "📚 Library":
            lib_page_size = str_lit.selectbox(
                "Per Page",
                options=[25, 50, 100],
                index=0,
                key="lib_page_size_select",
                on_change=lambda: str_lit.session_state.update({"lib_page": 1}),
            )

            paged_library, total_lib_items = get_user_library_paginated(
                user_id=user["id"],
                limit=10000 if selected_tags else lib_page_size,
                offset=0 if selected_tags else (str_lit.session_state.lib_page - 1) * lib_page_size,
                search_query=lib_query if lib_query else None,
                sort_by=lib_sort_option,
            )

            if selected_tags and paged_library:
                filtered = [item for item in paged_library if any(t in (item.get("tags") or []) for t in selected_tags)]
                total_lib_items = len(filtered)
                offset = (str_lit.session_state.lib_page - 1) * lib_page_size
                paged_library = filtered[offset : offset + lib_page_size]

            total_lib_pages = max(1, (total_lib_items + lib_page_size - 1) // lib_page_size)

            if str_lit.session_state.lib_page > total_lib_pages:
                str_lit.session_state.lib_page = total_lib_pages

            if not paged_library:
                str_lit.info("No matching cards in your library.")
            else:
                for item in paged_library:
                    render_library_row(item, sorted_tags)

                render_pagination_bar(
                    "lib_page",
                    str_lit.session_state.lib_page,
                    total_lib_pages,
                    total_lib_items,
                    key_suffix="bottom",
                )

        elif current_tab == "❤️ Wishlist":
            wish_page_size = str_lit.selectbox(
                "Per Page",
                options=[25, 50, 100],
                index=0,
                key="wish_page_size_select",
                on_change=lambda: str_lit.session_state.update({"wish_page": 1}),
            )

            offset = (str_lit.session_state.wish_page - 1) * wish_page_size
            paged_wishlist, total_wish_items = get_user_wishlist_paginated(
                user_id=user["id"],
                limit=wish_page_size,
                offset=offset,
                search_query=wish_query if wish_query else None,
                sort_by=wish_sort_option,
            )
            total_wish_pages = max(1, (total_wish_items + wish_page_size - 1) // wish_page_size)

            if str_lit.session_state.wish_page > total_wish_pages:
                str_lit.session_state.wish_page = total_wish_pages

            if not paged_wishlist:
                str_lit.info("No matching items in your wishlist.")
            else:
                for idx, wish_item in enumerate(paged_wishlist):
                    render_wishlist_row(wish_item, idx)

                render_pagination_bar(
                    "wish_page",
                    str_lit.session_state.wish_page,
                    total_wish_pages,
                    total_wish_items,
                    key_suffix="bottom",
                )