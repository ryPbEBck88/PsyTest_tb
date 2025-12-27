import sqlite3
from datetime import datetime

DB_PATH = "/data/bot.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TEXT,
            promo_sent INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0
        );
        """
    )
    conn.commit()
    conn.close()


def save_user(message):
    """Сохраняем пользователя, если его ещё нет."""
    save_user_from_user(message.from_user)


def save_user_from_user(user):
    """Сохраняет пользователя из объекта User (from aiogram.types.User)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT OR IGNORE INTO users (telegram_id, username, first_name, last_name, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def mark_promo_sent(telegram_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE users SET promo_sent = 1 WHERE telegram_id = ?", # promo_sent = 1
        (telegram_id,),
    )
    conn.commit()
    conn.close()


def is_promo_sent(telegram_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT promo_sent FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = cur.fetchone()
    conn.close()
    return bool(row and row[0])


def get_user_first_name(telegram_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT first_name FROM users WHERE telegram_id = ?",
        (telegram_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row and row[0]:
        return row[0]
    return "друг"  # fallback, если имени нет


# В db.py добавляем функцию проверки
def user_exists(telegram_id: int) -> bool:
    """Проверяет, существует ли пользователь в БД"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


def update_score(telegram_id: int, score: int):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "UPDATE users SET score = ? WHERE telegram_id = ?",
            (score, telegram_id),
        )
        con.commit()


def get_recent_users(limit: int = 10) -> list[tuple]:
    """
    Получает последних N пользователей, отсортированных по дате создания (новые первые)
    Возвращает список кортежей: (telegram_id, username, first_name, last_name, created_at, score)
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT telegram_id, username, first_name, last_name, created_at, score FROM users ORDER BY created_at DESC LIMIT ?",
        (limit,),
    )
    users = cur.fetchall()
    conn.close()
    return users