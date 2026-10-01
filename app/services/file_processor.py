# app/services/file_processor.py
import io
import openpyxl
from docx import Document
from pptx import Presentation
import markitdown

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


async def process_file(filename: str, content: bytes) -> tuple[bytes, str]:
    """
    Convierte archivos a formato que Gemini pueda leer.
    Devuelve (contenido_procesado, mime_type).
    """

    if len(content) > MAX_FILE_SIZE:
        raise ValueError("El archivo excede los 20 MB permitidos")

    ext = filename.split(".")[-1].lower() if "." in filename else ""

    # Formatos nativos de Gemini
    native_formats = {
        "pdf": "application/pdf",
        "txt": "text/plain",
        "html": "text/html",
        "htm": "text/html",
        "csv": "text/csv",
        "rtf": "text/rtf",
        "json": "application/json",
        "xml": "text/xml",
    }
    if ext in native_formats:
        return content, native_formats[ext]

    # Imágenes
    image_formats = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif": "image/gif",
        "bmp": "image/bmp",
    }
    if ext in image_formats:
        return content, image_formats[ext]

    # Audio
    audio_formats = {
        "mp3": "audio/mp3",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "m4a": "audio/m4a",
        "flac": "audio/flac",
        "aac": "audio/aac",
        "webm": "audio/webm",
    }
    if ext in audio_formats:
        return content, audio_formats[ext]

    # Video (Gemini soporta algunos)
    video_formats = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mov": "video/quicktime",
    }
    if ext in video_formats:
        return content, video_formats[ext]

    # Word (.docx, .doc)
    if ext in ["docx", "doc"]:
        try:
            md = markitdown.convert_stream(
                io.BytesIO(content),
                file_extension=ext
            )
            return md.text_content.encode("utf-8"), "text/plain"
        except Exception as e:
            raise ValueError(f"Error procesando Word: {str(e)}")

    # Excel (.xlsx, .xls)
    if ext in ["xlsx", "xls"]:
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            output = io.StringIO()
            for sheet in wb.worksheets:
                output.write(f"\n=== Hoja: {sheet.title} ===\n")
                for row in sheet.iter_rows(values_only=True):
                    row_text = ",".join(
                        str(c) if c is not None else "" for c in row
                    )
                    output.write(row_text + "\n")
            return output.getvalue().encode("utf-8"), "text/plain"
        except Exception as e:
            raise ValueError(f"Error procesando Excel: {str(e)}")

    # PowerPoint (.pptx, .ppt)
    if ext in ["pptx", "ppt"]:
        try:
            prs = Presentation(io.BytesIO(content))
            text = []
            for i, slide in enumerate(prs.slides, 1):
                text.append(f"\n=== Diapositiva {i} ===")
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        text.append(shape.text)
            return "\n".join(text).encode("utf-8"), "text/plain"
        except Exception as e:
            raise ValueError(f"Error procesando PowerPoint: {str(e)}")

    raise ValueError(f"Formato no soportado: .{ext}")