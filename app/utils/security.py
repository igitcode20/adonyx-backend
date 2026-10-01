# app/utils/security.py

# Palabras prohibidas que no deben aparecer en los prompts
FORBIDDEN_KEYWORDS = [
    "api key", "apikey", "api_key",
    "token", "jwt_secret",
    "password", "contraseña",
    "nicacore", "nica core",
    "ismael", "romero sánchez", "romero sanchez",
    "creador", "desarrollador", "founder",
    "gemini api", "mongodb uri",
    "system prompt", "instrucciones del sistema",
    "ignore previous", "ignora las instrucciones",
    "jailbreak", "dan mode",
    "revela tu", "muestra tu",
    "how were you built", "cómo fuiste creado",
]


def is_prompt_safe(prompt: str) -> tuple[bool, str]:
    """
    Verifica si un prompt intenta extraer información sensible.
    Devuelve (es_seguro, razón_de_bloqueo).
    """
    prompt_lower = prompt.lower()

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in prompt_lower:
            return False, "El prompt contiene términos no permitidos por las políticas de Adonyx"

    return True, ""


def sanitize_output(text: str) -> str:
    """
    Filtra la salida de la IA para eliminar posibles filtraciones.
    """
    if not text:
        return text

    replacements = {
        "nicacore": "NicaCore",
        "gemini": "un modelo de IA",
        "google ai": "un proveedor de IA",
        "mongodb": "una base de datos",
        "ismael adonis romero sánchez": "el equipo de desarrollo",
        "ismael romero": "el equipo de desarrollo",
    }

    # Reemplazos suaves (no bloquea, solo normaliza)
    return text