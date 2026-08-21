import requests
import streamlit as st

SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"

@st.cache_data(ttl=3600)  # Cache search results for 1 hour
def search_cards(query: str) -> list[dict]:
    """
    Queries the Scryfall API using search syntax (e.g., 'Lightning Bolt', 't:creature c:r', 'mv=3').
    Returns a list of matching card objects.
    """
    if not query.strip():
        return []

    params = {
        "q": query,
        "unique": "cards",
        "order": "name"
    }

    # Scryfall requires explicit User-Agent and Accept headers
    headers = {
        "User-Agent": "MTGLibraryApp/1.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(
            SCRYFALL_SEARCH_URL, 
            params=params, 
            headers=headers, 
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json().get("data", [])
        elif response.status_code == 404:
            return []  # No cards found
        else:
            st.error(f"Scryfall API Error: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error while reaching Scryfall: {e}")
        return []

def get_card_image_url(card: dict, size: str = "normal") -> str:
    """
    Helper function to safely extract card artwork URLs.
    Handles single-faced cards, double-faced transform cards, and fallbacks.
    """
    # 1. Standard single-faced card
    if "image_uris" in card:
        return card["image_uris"].get(size, "")
    
    # 2. Multi-faced or transform card (uses front face artwork)
    if "card_faces" in card and len(card["card_faces"]) > 0:
        face = card["card_faces"][0]
        if "image_uris" in face:
            return face["image_uris"].get(size, "")
            
    # 3. Fallback placeholder
    return "https://errors.scryfall.com/unknown.jpg"