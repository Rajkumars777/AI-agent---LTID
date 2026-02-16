import sqlite3
import os
from typing import Any, Optional

# Simple SQLite-based preference store
# For a "World-Class" agent, this would be a Vector DB (ChromaDB/FAISS),
# but for a local desktop agent, a structured relational store is more reliable for direct preferences.

DATABASE_PATH = os.path.join(os.getcwd(), "backend", "memory.db")

def init_memory():
    """Builds the memory schema."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT,
            category TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def set_preference(key: str, value: Any, category: str = "general"):
    """Stores or updates a user preference."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO preferences (key, value, category, last_updated)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET 
            value=excluded.value,
            last_updated=excluded.last_updated
    ''', (key, str(value), category))
    conn.commit()
    conn.close()
    print(f"Memory: Saved preference {key} = {value}")

def get_preference(key: str) -> Optional[str]:
    """Retrieves a user preference."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM preferences WHERE key = ?', (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# Initialize on import
init_memory()
