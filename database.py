"""Работа с базой данных SQLite"""
import aiosqlite
import secrets
import string
from datetime import datetime
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH


def generate_ref_code(length: int = 8) -> str:
    """Генерация уникального реферального кода"""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    async def init(self):
        """Инициализация таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language_code TEXT,
                    is_premium INTEGER DEFAULT 0,
                    ref_code TEXT UNIQUE,
                    created_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sender_id INTEGER,
                    receiver_id INTEGER,
                    ref_code TEXT,
                    created_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_message_id INTEGER,
                    owner_chat_id INTEGER,
                    sender_id INTEGER,
                    receiver_id INTEGER,
                    content_type TEXT,
                    created_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS admin_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_users INTEGER DEFAULT 0,
                    total_messages INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            """)
            await db.commit()

    async def add_user(self, user_id: int, username: Optional[str], first_name: Optional[str],
                       last_name: Optional[str], language_code: Optional[str], is_premium: bool = False) -> str:
        """Добавление пользователя или обновление данных"""
        ref_code = generate_ref_code()
        created_at = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, language_code, is_premium, ref_code, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, username, first_name, last_name, language_code, int(is_premium), ref_code, created_at))
                await db.commit()
                return ref_code
            except aiosqlite.IntegrityError:
                # Пользователь уже существует — получаем его ref_code
                cursor = await db.execute("SELECT ref_code FROM users WHERE user_id = ?", (user_id,))
                row = await cursor.fetchone()
                # Обновляем данные на случай изменений
                await db.execute("""
                    UPDATE users SET username = ?, first_name = ?, last_name = ?, language_code = ?, is_premium = ?
                    WHERE user_id = ?
                """, (username, first_name, last_name, language_code, int(is_premium), user_id))
                await db.commit()
                return row[0] if row else ref_code

    async def get_user_by_ref(self, ref_code: str) -> Optional[Dict[str, Any]]:
        """Получение пользователя по реферальному коду"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE ref_code = ?", (ref_code,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_session(self, sender_id: int, receiver_id: int, ref_code: str) -> int:
        """Создание сессии анонимного общения"""
        created_at = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO sessions (sender_id, receiver_id, ref_code, created_at)
                VALUES (?, ?, ?, ?)
            """, (sender_id, receiver_id, ref_code, created_at))
            await db.commit()
            return cursor.lastrowid

    async def get_active_session(self, sender_id: int) -> Optional[Dict[str, Any]]:
        """Получение активной сессии отправителя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM sessions WHERE sender_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (sender_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def save_message_mapping(self, bot_message_id: int, owner_chat_id: int,
                                    sender_id: int, receiver_id: int, content_type: str):
        """Сохранение связи сообщения бота с отправителем"""
        created_at = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO messages (bot_message_id, owner_chat_id, sender_id, receiver_id, content_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bot_message_id, owner_chat_id, sender_id, receiver_id, content_type, created_at))
            await db.commit()

    async def get_message_mapping(self, bot_message_id: int, owner_chat_id: int) -> Optional[Dict[str, Any]]:
        """Получение связи по ID сообщения бота"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM messages WHERE bot_message_id = ? AND owner_chat_id = ?
            """, (bot_message_id, owner_chat_id))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_total_users(self) -> int:
        """Общее количество пользователей"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_total_messages(self) -> int:
        """Общее количество сообщений"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_all_user_ids(self) -> List[int]:
        """Получение всех user_id для рассылки"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def clear_session(self, sender_id: int):
        """Очистка сессии отправителя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM sessions WHERE sender_id = ?", (sender_id,))
            await db.commit()


db = Database()
