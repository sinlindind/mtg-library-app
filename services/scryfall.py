import requests
import streamlit as st

SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"

@st.cache_data(ttl=3600)
def search_cards(query: str) -> list[dict]:
    """Queries Scryfall API using full search syntax."""
    if not query.strip():
        return []

    params = {
        "q": query,
        "unique": "cards",
        "order": "name"
    }

    # Scryfall requires custom User-Agent and Accept headers
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
            return []  # No cards matched the search
        else:
            st.error(f"Scryfall API Error: {response.status_code}")
            return []
            
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return []