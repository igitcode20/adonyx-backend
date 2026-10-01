# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Credenciales
MONGODB_URI = os.getenv("MONGODB_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

# Límites de la Beta
MAX_BETA_USERS = int(os.getenv("MAX_BETA_USERS", "50"))
DAILY_IMAGE_LIMIT = int(os.getenv("DAILY_IMAGE_LIMIT", "10"))
MAX_CONVERSATIONS = int(os.getenv("MAX_CONVERSATIONS", "5"))
DAILY_MESSAGE_LIMIT = int(os.getenv("DAILY_MESSAGE_LIMIT", "100"))

# Validación de variables críticas
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI no está configurada en el .env")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY no está configurada en el .env")
if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET debe tener al menos 32 caracteres")

print("[CONFIG] Variables de entorno cargadas correctamente")