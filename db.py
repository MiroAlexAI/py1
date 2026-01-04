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
        
        # Набор таблиц для первого типа промптов (стандартный)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                prompt TEXT NOT NULL,
                tags TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_id INTEGER,
                full_prompt TEXT,
                model_name TEXT,
                response TEXT,
                date TEXT,
                resp_time REAL,
                status TEXT,
                FOREIGN KEY (prompt_id) REFERENCES prompts(id) ON DELETE CASCADE
            )
        """)
        
        # Миграция: Проверяем наличие колонки full_prompt
        cursor.execute("PRAGMA table_info(results)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'full_prompt' not in columns:
            cursor.execute("ALTER TABLE results ADD COLUMN full_prompt TEXT")
        if 'resp_time' not in columns:
            cursor.execute("ALTER TABLE results ADD COLUMN resp_time REAL")
        if 'status' not in columns:
            cursor.execute("ALTER TABLE results ADD COLUMN status TEXT")

        # Таблицы для второго типа промптов
        cursor.execute("CREATE TABLE IF NOT EXISTS prompts2 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, prompt TEXT, tags TEXT)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT, prompt_id INTEGER, model_name TEXT, response TEXT, date TEXT,
                FOREIGN KEY (prompt_id) REFERENCES prompts2(id) ON DELETE CASCADE
            )
        """)

        # Таблицы для третьего типа промптов
        cursor.execute("CREATE TABLE IF NOT EXISTS prompts3 (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, prompt TEXT, tags TEXT)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results3 (
                id INTEGER PRIMARY KEY AUTOINCREMENT, prompt_id INTEGER, model_name TEXT, response TEXT, date TEXT,
                FOREIGN KEY (prompt_id) REFERENCES prompts3(id) ON DELETE CASCADE
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
        
        # Таблица настроек
        cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        
        # Таблица заметок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                tag TEXT,
                title TEXT,
                content TEXT
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

def add_prompt(text, tags="", table="prompts"):
    with get_connection() as conn:
        cursor = conn.cursor()
        date_str = datetime.now().isoformat()
        cursor.execute(f"INSERT INTO {table} (date, prompt, tags) VALUES (?, ?, ?)", (date_str, text, tags))
        conn.commit()
        return cursor.lastrowid

def get_prompts(table="prompts"):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, date, prompt, tags FROM {table} ORDER BY date DESC")
        return cursor.fetchall()

def delete_prompt(prompt_id, table="prompts"):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (prompt_id,))
        conn.commit()

def get_prompt_id(text, table="prompts"):
    """Возвращает ID промпта, если он уже есть в базе."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id FROM {table} WHERE prompt = ? ORDER BY date DESC LIMIT 1", (text,))
        row = cursor.fetchone()
        return row[0] if row else None

# --- Сохранение результатов ---

def save_result(prompt_id, model_name, response, table="results", full_prompt="", resp_time=0.0, status="Success"):
    with get_connection() as conn:
        cursor = conn.cursor()
        date_str = datetime.now().isoformat()
        if table == "results":
            cursor.execute(f"INSERT INTO {table} (prompt_id, model_name, response, date, full_prompt, resp_time, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                           (prompt_id, model_name, response, date_str, full_prompt, resp_time, status))
        else:
            cursor.execute(f"INSERT INTO {table} (prompt_id, model_name, response, date) VALUES (?, ?, ?, ?)",
                           (prompt_id, model_name, response, date_str))
        conn.commit()

def get_model_metrics(model_name):
    """Возвращает (среднее_время, количество_ошибок) для модели."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT AVG(resp_time), COUNT(*) FILTER (WHERE status LIKE 'Error%')
            FROM results 
            WHERE model_name = ? AND resp_time > 0
        """, (model_name,))
        res = cursor.fetchone()
        return (round(res[0], 2) if res[0] else 0.0, res[1] or 0)

def get_all_metrics():
    """Возвращает метрики для всех моделей."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT model_name, AVG(resp_time), COUNT(*) FILTER (WHERE status LIKE 'Error%')
            FROM results 
            WHERE resp_time > 0
            GROUP BY model_name
        """)
        return {row[0]: {"avg_time": round(row[1], 2), "errors": row[2]} for row in cursor.fetchall()}

def get_model_popularity_rating(limit=5):
    """Возвращает список самых используемых моделей на основе сохраненных результатов."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT model_name, COUNT(*) as cnt 
            FROM results 
            GROUP BY model_name 
            ORDER BY cnt DESC 
            LIMIT ?
        """, (limit,))
        return cursor.fetchall()

def get_results(prompt_id=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if prompt_id:
            cursor.execute("SELECT id, prompt_id, model_name, response, date, full_prompt FROM results WHERE prompt_id = ? ORDER BY date DESC", (prompt_id,))
        else:
            cursor.execute("SELECT id, prompt_id, model_name, response, date, full_prompt FROM results ORDER BY date DESC")
        return cursor.fetchall()

def delete_result(result_id):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM results WHERE id = ?", (result_id,))
        conn.commit()

# --- Settings Management ---

def get_setting(key, default=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else default

def set_setting(key, value):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
