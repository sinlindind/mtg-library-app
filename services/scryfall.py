import requests
import streamlit as st

SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"

@st.cache_data(ttl=3600)  # Cache results for 1 hour to prevent spamming Scryfall
def search_cards(query: str) -> list[dict]:
    """
    Queries Scryfall API using full syntax (e.g., 'lightning bolt', 't:creature c:r', 'mv=3').
    Returns a list of parsed card objects.
    """
    if not query.strip():
        return []

    params = {
        "q": query,
        "unique": "cards",
        "order": "name"
    }

    try:
        response = requests.get(SCRYFALL_SEARCH_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 404:
            return []  # No matching cards
        else:
            st.error(f"Scryfall API Error: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return []

def get_card_image_url(card: dict, size: str = "normal") -> str:
    """Helper to retrieve card image URLs, handling single and double-faced cards."""
    if "image_uris" in card:
        return card["image_uris"].get(size, "")
    
    # Handle multi-faced/transform cards
    if "card_faces" in card and len(card["card_faces"]) > 0:
        face = card["card_faces"][0]
        if "image_uris" in face:
            return face["image_uris"].get(size, "")
            
    return "https://errors.scryfall.com/unknown.jpg"