# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

from app.database import create_indexes
from app.routes import auth_routes, chat_routes, file_routes

app = FastAPI(
    title="Adonyx API",
    version="1.0.0",
    description="API de inteligencia artificial para estudiantes - NicaCore",
    contact={
        "name": "NicaCore",
        "url": "https://nicacore.com",
    },
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://adonyx-frontend.vercel.app",
        "https://adonyx-frontend-git-master-ismael-s-projects19.vercel.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Manejo global de errores
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


@app.on_event("startup")
async def startup():
    print("[STARTUP] Iniciando Adonyx API...")
    await create_indexes()
    print("[STARTUP] Listo")


# Registrar routers
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(file_routes.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "Adonyx API",
        "version": "1.0.0",
    }


@app.get("/")
async def root():
    return {
        "message": "Adonyx API - NicaCore",
        "docs": "/docs",
    }