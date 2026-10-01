# app/routes/file_routes.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.auth import get_current_user
from app.services.file_processor import process_file

router = APIRouter(prefix="/api/files", tags=["files"])


@router.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Analiza un archivo y confirma que se puede procesar."""
    try:
        content = await file.read()
        processed, mime_type = await process_file(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "filename": file.filename,
        "mime_type": mime_type,
        "size_bytes": len(processed),
        "message": "Archivo procesado. Envíalo en el chat para que Adonyx lo analice.",
    }