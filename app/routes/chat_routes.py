# app/routes/chat_routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from datetime import datetime, timezone
from bson import ObjectId
import base64

from app.auth import get_current_user
from app.database import users_collection, conversations_collection
from app.services.gemini_service import chat_with_gemini, generate_image
from app.services.file_processor import process_file
from app.config import (
    DAILY_IMAGE_LIMIT,
    MAX_CONVERSATIONS,
    DAILY_MESSAGE_LIMIT,
)

router = APIRouter(prefix="/api", tags=["chat"])


async def check_and_reset_quota(user: dict) -> dict:
    """Verifica y resetea los cupos diarios si es necesario."""
    today = datetime.now(timezone.utc).date()
    last_reset = user["usage"].get("last_reset")

    if last_reset:
        last_reset_date = (
            last_reset.date() if hasattr(last_reset, "date") else last_reset
        )
        if last_reset_date < today:
            await users_collection.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "usage.messages_today": 0,
                        "usage.images_today": 0,
                        "usage.last_reset": datetime.now(timezone.utc),
                    }
                },
            )
            user["usage"]["messages_today"] = 0
            user["usage"]["images_today"] = 0

    return user


@router.post("/chat")
async def chat(
    message: str = Form(...),
    conversation_id: str = Form(None),
    file: UploadFile = File(None),
    user: dict = Depends(get_current_user),
):
    user = await check_and_reset_quota(user)

    # 1. Verificar límite de mensajes diarios
    if user["usage"]["messages_today"] >= DAILY_MESSAGE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Límite diario de mensajes alcanzado. Vuelve mañana.",
        )

    # 2. Procesar archivo si existe
    file_content = None
    mime_type = None
    if file:
        try:
            content = await file.read()
            file_content, mime_type = await process_file(file.filename, content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 3. Obtener historial si hay conversación
    history = []
    if conversation_id:
        try:
            conv = await conversations_collection.find_one(
                {
                    "_id": ObjectId(conversation_id),
                    "user_id": user["_id"],
                }
            )
            if conv:
                history = conv.get("messages", [])[-10:]
        except Exception:
            raise HTTPException(status_code=400, detail="ID de conversación inválido")

    # 4. Llamar a Gemini
    try:
        reply = await chat_with_gemini(message, file_content, mime_type, history)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar con la IA: {str(e)}",
        )

    # 5. Crear o actualizar conversación
    now = datetime.now(timezone.utc)

    if not conversation_id:
        # Verificar límite de conversaciones
        conv_count = await conversations_collection.count_documents(
            {"user_id": user["_id"]}
        )

        if conv_count >= MAX_CONVERSATIONS:
            # Eliminar la más antigua
            oldest = await conversations_collection.find_one(
                {"user_id": user["_id"]},
                sort=[("updated_at", 1)],
            )
            if oldest:
                await conversations_collection.delete_one({"_id": oldest["_id"]})

        conv_doc = {
            "user_id": user["_id"],
            "title": message[:60],
            "created_at": now,
            "updated_at": now,
            "messages": [],
        }
        result = await conversations_collection.insert_one(conv_doc)
        conversation_id = str(result.inserted_id)

    # 6. Guardar mensajes (solo últimos 50)
    await conversations_collection.update_one(
        {"_id": ObjectId(conversation_id)},
        {
            "$push": {
                "messages": {
                    "$each": [
                        {"role": "user", "content": message, "timestamp": now},
                        {"role": "assistant", "content": reply, "timestamp": now},
                    ],
                    "$slice": -50,
                }
            },
            "$set": {"updated_at": now},
        },
    )

    # 7. Incrementar contador de mensajes
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$inc": {"usage.messages_today": 1}},
    )

    return {"reply": reply, "conversation_id": conversation_id}


@router.post("/generate-image")
async def generate_image_route(
    prompt: str = Form(...),
    aspect_ratio: str = Form("1:1"),
    user: dict = Depends(get_current_user),
):
    user = await check_and_reset_quota(user)

    # Verificar límite diario de imágenes
    if user["usage"]["images_today"] >= DAILY_IMAGE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Límite diario de {DAILY_IMAGE_LIMIT} imágenes alcanzado",
        )

    try:
        image_data = await generate_image(prompt, aspect_ratio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generando imagen: {str(e)}",
        )

    # Convertir a base64
    image_base64 = base64.b64encode(image_data).decode("utf-8")

    # Incrementar contador
    await users_collection.update_one(
        {"_id": user["_id"]},
        {"$inc": {"usage.images_today": 1}},
    )

    remaining = DAILY_IMAGE_LIMIT - user["usage"]["images_today"] - 1

    return {
        "image_url": f"data:image/png;base64,{image_base64}",
        "remaining": remaining,
    }


@router.get("/conversations")
async def list_conversations(user: dict = Depends(get_current_user)):
    """Lista las conversaciones del usuario (máximo 5)."""
    cursor = (
        conversations_collection.find(
            {"user_id": user["_id"]},
            {"messages": {"$slice": -1}},
        )
        .sort("updated_at", -1)
        .limit(MAX_CONVERSATIONS)
    )

    convs = []
    async for conv in cursor:
        last_msg = conv.get("messages", [{}])
        last_content = last_msg[-1].get("content", "") if last_msg else ""
        convs.append(
            {
                "id": str(conv["_id"]),
                "title": conv.get("title", "Sin título"),
                "updated_at": conv.get("updated_at"),
                "last_message": last_content[:100],
            }
        )

    return {"conversations": convs}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene el contenido completo de una conversación."""
    try:
        conv = await conversations_collection.find_one(
            {
                "_id": ObjectId(conversation_id),
                "user_id": user["_id"],
            }
        )
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    return {
        "id": str(conv["_id"]),
        "title": conv.get("title"),
        "messages": [
            {"role": m["role"], "content": m["content"]}
            for m in conv.get("messages", [])
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: dict = Depends(get_current_user),
):
    """Elimina una conversación específica."""
    try:
        result = await conversations_collection.delete_one(
            {
                "_id": ObjectId(conversation_id),
                "user_id": user["_id"],
            }
        )
    except Exception:
        raise HTTPException(status_code=400, detail="ID inválido")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")

    return {"message": "Conversación eliminada"}