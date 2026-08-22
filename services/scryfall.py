import requests
import streamlit as st

SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"

@st.cache_data(ttl=3600)
def search_cards(query: str) -> list[dict]:
    """Queries Scryfall API returning all printings and versions of matching cards."""
    if not query.strip():
        return []

    params = {
        "q": query,
        "unique": "prints",  # <--- Changed from 'cards' to 'prints' to show every version/set
        "order": "released", # Sorts printings chronologically (or use 'set')
        "dir": "desc"        # Newest releases first
    }

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
            return []
        else:
            st.error(f"Scryfall API Error: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return []

def get_card_image_url(card: dict, size: str = "large") -> str:
    """Helper to extract card images safely."""
    if "image_uris" in card:
        return card["image_uris"].get(size, card["image_uris"].get("normal", ""))
    
    if "card_faces" in card and len(card["card_faces"]) > 0:
        face = card["card_faces"][0]
        if "image_uris" in face:
            return face["image_uris"].get(size, face["image_uris"].get("normal", ""))
            
    return "https://errors.scryfall.com/unknown.jpg"

def get_card_by_id(scryfall_id: str) -> dict:
    """Fetches full card JSON payload from Scryfall by its ID."""
    if not scryfall_id:
        return {}
        
    url = f"https://api.scryfall.com/cards/{scryfall_id}"
    headers = {
        "User-Agent": "MTGLibraryApp/1.0",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except requests.exceptions.RequestException:
        return {}
    
def autocomplete_cards(query: str) -> list[str]:
    """Fetches up to 20 matching card name suggestions from Scryfall."""
    if not query or len(query.strip()) < 2:
        return []

    url = "https://api.scryfall.com/cards/autocomplete"
    params = {"q": query}
    headers = {
        "User-Agent": "MTGLibraryApp/1.0",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            return response.json().get("data", [])
        return []
    except requests.exceptions.RequestException:
        return []