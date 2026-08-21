import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Database Connection Helper
def get_db_connection():
    """
    Establishes and returns a connection to the PostgreSQL database.
    Assumes DATABASE_URL is stored in your environment variables.
    """
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(database_url)

# ==========================================
# USER MANAGEMENT FUNCTIONS
# ==========================================

def create_user(username: str, email: str, password_hash: str, salt: str, verification_token: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        INSERT INTO users (username, email, password_hash, verification_token, is_verified)
        VALUES (%s, %s, %s, %s, FALSE)
        RETURNING id;
    """
    try:
        full_hash = f"{password_hash}:{salt}"
        cursor.execute(query, (username, email, full_hash, verification_token))
        user_id = cursor.fetchone()[0]
        conn.commit()
        return user_id
    finally:
        cursor.close()
        conn.close()

def get_user_by_username(username: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM users WHERE username = %s;"
    try:
        cursor.execute(query, (username,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def get_user_by_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    query = "SELECT * FROM users WHERE email = %s;"
    try:
        cursor.execute(query, (email,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

def verify_user_email(email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "UPDATE users SET is_verified = TRUE, verification_token = NULL WHERE email = %s;"
    try:
        cursor.execute(query, (email,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

# ==========================================
# MASTER LIBRARY FUNCTIONS (user_cards)
# ==========================================

def init_user_cards_table():
    """
    Ensures the user_cards table and unique constraint exist in PostgreSQL.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    CREATE TABLE IF NOT EXISTS user_cards (
        id BIGSERIAL PRIMARY KEY,
        user_id UUID NOT NULL,
        scryfall_id TEXT NOT NULL,
        finish TEXT NOT NULL DEFAULT 'nonfoil',
        condition TEXT DEFAULT 'Near Mint',
        language TEXT DEFAULT 'en',
        quantity INTEGER NOT NULL DEFAULT 1,
        purchase_price NUMERIC(10, 2) DEFAULT NULL,
        acquired_date DATE DEFAULT CURRENT_DATE,
        notes TEXT DEFAULT NULL,
        CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_user_cards_user_id ON user_cards(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_cards_scryfall_id ON user_cards(scryfall_id);
    
    ALTER TABLE user_cards DROP CONSTRAINT IF EXISTS unique_user_card_entry;
    ALTER TABLE user_cards ADD CONSTRAINT unique_user_card_entry UNIQUE (user_id, scryfall_id, finish, condition);
    """
    try:
        cursor.execute(query)
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def add_card_to_library(user_id: str, scryfall_id: str, finish: str = "nonfoil", 
                        quantity: int = 1, condition: str = "Near Mint", 
                        purchase_price: float = None, notes: str = None):
    """
    Adds a card to the user's master library. If a card with the exact same
    finish and condition already exists for this user, it updates the quantity.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    INSERT INTO user_cards (user_id, scryfall_id, finish, condition, quantity, purchase_price, notes)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (user_id, scryfall_id, finish, condition) 
    DO UPDATE SET quantity = user_cards.quantity + EXCLUDED.quantity;
    """
    try:
        cursor.execute(query, (user_id, scryfall_id, finish, condition, quantity, purchase_price, notes))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def get_user_library(user_id: str):
    """
    Fetches all card records in the user's master library.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = """
    SELECT * FROM user_cards 
    WHERE user_id = %s 
    ORDER BY acquired_date DESC;
    """
    try:
        cursor.execute(query, (user_id,))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

def remove_card_from_library(user_cards_id: int, user_id: str):
    """
    Deletes a specific card record from the user's library.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "DELETE FROM user_cards WHERE id = %s AND user_id = %s;"
    try:
        cursor.execute(query, (user_cards_id, user_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()