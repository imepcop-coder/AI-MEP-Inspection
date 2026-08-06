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


class AIUnavailable(Exception):
    pass


def analyze_image(image_path):
    if not GEMINI_API_KEY:
        raise AIUnavailable("Gemini AI provider is not configured")
    # Not implemented for streaming in this environment — fallback
    raise AIUnavailable("Gemini provider not configured for live analysis in this environment")


def generate_text(prompt: str, system_prompt: str | None = None) -> str:
    if not GEMINI_API_KEY:
        raise AIUnavailable("Gemini AI provider is not configured")
    # Not implemented for live generation here
    raise AIUnavailable("Gemini provider not configured for live generation in this environment")