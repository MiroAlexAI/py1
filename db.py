import sqlite3
import os
from datetime import datetime

DB_NAME = "chatlist.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    """Инициализация таблиц базы данных."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Таблица промтов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT
            )
        """)
        
        # Таблица моделей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                name TEXT PRIMARY KEY,
                api_url TEXT NOT NULL,
                api_id TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Таблица результатов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER,
                model_name TEXT,
                response TEXT,
                date TEXT,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица настроек
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()

# --- CRUD для моделей ---

def get_models(only_active=False):
    with get_connection() as conn:
        cursor = conn.cursor()
        if only_active:
            cursor.execute("SELECT name, api_url, api_id, is_active FROM models WHERE is_active = 1")
        else:
            cursor.execute("SELECT name, api_url, api_id, is_active FROM models")
        return cursor.fetchall()

def add_model(name, api_url, api_id, is_active=1):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO models (name, api_url, api_id, is_active) VALUES (?, ?, ?, ?)",
                       (name, api_url, api_id, is_active))
        conn.commit()

def delete_model(name):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM models WHERE name = ?", (name,))
        conn.commit()

# --- CRUD для промтов ---

def add_prompt(text, tags=""):
    with get_connection() as conn:
        cursor = conn.cursor()
        date_str = datetime.now().isoformat()
        cursor.execute("INSERT INTO prompts (date, prompt, tags) VALUES (?, ?, ?)", (date_str, text, tags))
        conn.commit()
        return cursor.lastrowid

def get_prompts():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, date, prompt, tags FROM prompts ORDER BY date DESC")
        return cursor.fetchall()

# --- Сохранение результатов ---

def save_result(prompt_id, model_name, response):
    with get_connection() as conn:
        cursor = conn.cursor()
        date_str = datetime.now().isoformat()
        cursor.execute("INSERT INTO results (prompt_id, model_name, response, date) VALUES (?, ?, ?, ?)",
                       (prompt_id, model_name, response, date_str))
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
