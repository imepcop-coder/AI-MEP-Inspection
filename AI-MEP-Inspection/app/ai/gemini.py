import json

from app.config import GEMINI_API_KEY


def _fallback_payload(message: str | None = None) -> str:
    payload = {
        "is_supported": True,
        "industry": "Construction",
        "discipline": "General",
        "location": "Unknown",
        "equipment": "Unknown",
        "category": "Quality",
        "severity": "Low",
        "snag_description": message or "Gemini AI provider is not configured. Review the image manually.",
        "recommendation": "Document the observation in the inspection report and verify it in the field.",
        "status": "Open",
    }
    return json.dumps(payload)


def analyze_image(image_path):
    if not GEMINI_API_KEY:
        return _fallback_payload("Gemini AI provider is not configured.")
    return _fallback_payload("Gemini provider is available but not configured for live analysis in this environment.")


def generate_text(prompt: str, system_prompt: str | None = None) -> str:
    if not GEMINI_API_KEY:
        return (
            "Gemini AI provider is not configured. Using fallback guidance to structure your request: "
            f"{prompt}"
        )
    return (
        "Gemini provider is not configured for live generation in this environment. "
        "Please review the request manually and structure the response around the available inspection context."
    )