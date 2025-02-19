# database.py
import aiosqlite

from config import DATABASE_FILE


async def create_tables():
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER UNIQUE,
                guild_id INTEGER,
                channel_id INTEGER,
                author_id INTEGER,
                author_name TEXT,
                content TEXT,
                jump_url TEXT,
                adder_user_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def add_quote(message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("""
            INSERT INTO quotes (message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, guild_id, channel_id, author_id, author_name, content, jump_url, adder_user_id))
        await db.commit()

async def get_quote_by_message_id(message_id):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("SELECT * FROM quotes WHERE message_id = ?", (message_id,))
        return await cursor.fetchone()

async def get_random_quote(channel_id = None):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        query = "SELECT * FROM quotes ORDER BY RANDOM() LIMIT 1"
        #add logic to select authors not shown recently
        cursor = await db.execute(query)
        return await cursor.fetchone()

async def get_quotes_by_search_term(term):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        cursor = await db.execute("SELECT * FROM quotes WHERE content LIKE ?", (f"%{term}%",))
        return await cursor.fetchall()

async def get_quotes_by_author(author_name):
    async with aiosqlite.connect(DATABASE_FILE) as db:
            cursor = await db.execute("SELECT * FROM quotes WHERE author_name LIKE ?", (f"%{author_name}%",))
            return await cursor.fetchall()

async def delete_quote(message_id):
    async with aiosqlite.connect(DATABASE_FILE) as db:
        await db.execute("DELETE FROM quotes WHERE message_id = ?", (message_id,))
        await db.commit()

async def get_last_author(channel_id): #gets the last shown author
    async with aiosqlite.connect(DATABASE_FILE) as db:
            cursor = await db.execute("SELECT author_id FROM quotes WHERE channel_id = ? ORDER BY id DESC LIMIT 1", (channel_id,))
            result = await cursor.fetchone()
            return result[0] if result else None

async def get_random_quote_not_by_author(author_id, channel_id):
        async with aiosqlite.connect(DATABASE_FILE) as db:
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE author_id != ? AND channel_id = ? ORDER BY RANDOM() LIMIT 1",
                (author_id, channel_id)
            )
            return await cursor.fetchone()
