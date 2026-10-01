# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import MONGODB_URI

client = AsyncIOMotorClient(MONGODB_URI)
db = client.adonyx

users_collection = db.users
conversations_collection = db.conversations
usage_logs_collection = db.usage_logs
image_generations_collection = db.image_generations


async def create_indexes():
    """Crea los índices necesarios en MongoDB."""
    try:
        await users_collection.create_index("email", unique=True)
        await conversations_collection.create_index(
            [("user_id", 1), ("updated_at", -1)]
        )
        await usage_logs_collection.create_index(
            [("user_id", 1), ("date", -1)]
        )
        await image_generations_collection.create_index(
            [("user_id", 1), ("created_at", -1)]
        )
        print("[DB] Índices creados correctamente")
    except Exception as e:
        print(f"[DB] Error creando índices: {e}")
        raise