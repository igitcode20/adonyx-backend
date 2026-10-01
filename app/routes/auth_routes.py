# app/routes/auth_routes.py
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from app.database import users_collection
from app.auth import hash_password, verify_password, create_token, get_current_user
from app.models import RegisterRequest, LoginRequest, UpdateProfileRequest
from app.config import MAX_BETA_USERS

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
async def register(data: RegisterRequest):
    # 1. Verificar límite de usuarios beta
    count = await users_collection.count_documents({})
    if count >= MAX_BETA_USERS:
        raise HTTPException(
            status_code=403,
            detail=f"La Beta alcanzó el límite de {MAX_BETA_USERS} usuarios"
        )

    # 2. Verificar email único
    existing = await users_collection.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=409, detail="El correo ya está registrado")

    # 3. Verificar aceptación de términos y cookies
    if not data.accept_terms or not data.accept_cookies:
        raise HTTPException(
            status_code=400,
            detail="Debes aceptar los términos y las cookies"
        )

    # 4. Crear el documento del usuario
    now = datetime.now(timezone.utc)
    user_doc = {
        "name": data.name,
        "email": data.email,
        "password_hash": hash_password(data.password),
        "birth_date": data.birth_date,
        "accepted_terms": True,
        "accepted_cookies": True,
        "terms_accepted_at": now,
        "created_at": now,
        "plan": "beta_free",
        "is_active": True,
        "role": "user",
        "usage": {
            "messages_today": 0,
            "images_today": 0,
            "last_reset": now,
        },
        "conversation_count": 0,
    }

    result = await users_collection.insert_one(user_doc)
    token = create_token(str(result.inserted_id))

    return {
        "token": token,
        "user": {
            "id": str(result.inserted_id),
            "name": data.name,
            "email": data.email,
            "birth_date": data.birth_date,
        },
    }


@router.post("/login")
async def login(data: LoginRequest):
    user = await users_collection.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Cuenta suspendida")

    token = create_token(str(user["_id"]))
    return {
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "birth_date": user.get("birth_date"),
        },
    }


@router.get("/me")
async def get_profile(user: dict = Depends(get_current_user)):
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "birth_date": user.get("birth_date"),
        "plan": user.get("plan", "beta_free"),
        "created_at": user.get("created_at"),
        "usage": user.get("usage", {}),
    }


@router.put("/me")
async def update_profile(
    data: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    update_data = {}
    if data.name:
        update_data["name"] = data.name
    if data.birth_date:
        update_data["birth_date"] = data.birth_date

    if update_data:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": update_data},
        )

    return {"message": "Perfil actualizado correctamente"}


@router.delete("/me")
async def delete_account(user: dict = Depends(get_current_user)):
    """Elimina la cuenta y todas sus conversaciones."""
    from app.database import conversations_collection

    await conversations_collection.delete_many({"user_id": user["_id"]})
    await users_collection.delete_one({"_id": user["_id"]})

    return {"message": "Cuenta eliminada permanentemente"}