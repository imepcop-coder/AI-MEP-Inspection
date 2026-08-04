import base64
import json

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - handled gracefully when dependency is absent
    OpenAI = None

from app.ai.prompt import PROMPT
from app.config import NVIDIA_API_KEY, NVIDIA_MODEL

client = None
if NVIDIA_API_KEY and OpenAI is not None:
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY,
        timeout=20,
        max_retries=2,
    )


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _clean_response(text: str) -> str:
    text = (text or "").strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1)

    if text.startswith("```"):
        text = text.replace("```", "", 1)

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def _fallback_payload(message: str | None = None) -> str:
    payload = {
        "is_supported": True,
        "industry": "Construction",
        "discipline": "General",
        "location": "Unknown",
        "equipment": "Unknown",
        "category": "Quality",
        "severity": "Low",
        "snag_description": message or "Inspection image processed with limited AI availability.",
        "recommendation": "Please review the uploaded image manually and document any findings in the inspection report.",
        "status": "Open",
    }
    return json.dumps(payload)


def analyze_image(image_path: str) -> str:
    image = encode_image(image_path)

    if not client:
        return _fallback_payload("NVIDIA AI provider is not configured.")

    try:
        response = client.chat.completions.create(
            model=NVIDIA_MODEL,
            temperature=0,
            max_tokens=900,
            timeout=20,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a senior Engineering QA/QC, HSE and Maintenance Inspector. "
                        "Analyze only visible conditions. "
                        "Return ONLY valid JSON. "
                        "Never return markdown or explanations. "
                        "If the image is unrelated to engineering, construction or maintenance, "
                        "return only: "
                        '{"is_supported":false,"message":"Uploaded image is not related to engineering, construction or maintenance."}'
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": PROMPT,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image}"
                            },
                        },
                    ],
                },
            ],
        )
        content = response.choices[0].message.content if response.choices else ""
        cleaned = _clean_response(content)
        if cleaned:
            return cleaned
    except Exception:
        pass

    return _fallback_payload("AI analysis could not be completed. Review the image manually.")


def generate_text(prompt: str, system_prompt: str | None = None) -> str:
    if not client:
        return (
            "The engineering copilot is currently running in fallback mode. "
            "Please provide more detail about the inspection issue, report template, or document type so I can structure a response."
        )

    try:
        response = client.chat.completions.create(
            model=NVIDIA_MODEL,
            temperature=0,
            max_tokens=700,
            timeout=20,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt or "You are a helpful engineering QA/QC assistant. Respond clearly and concisely.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        content = response.choices[0].message.content if response.choices else ""
        cleaned = _clean_response(content)
        if cleaned:
            return cleaned
    except Exception:
        pass

    return (
        "The engineering copilot could not reach the AI service. "
        "Please review the requested inspection topic manually and structure the response around the available project context."
    )
