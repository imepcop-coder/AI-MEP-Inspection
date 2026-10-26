import base64
import json
import traceback
from pathlib import Path
from typing import Any

try:
    from anthropic import AnthropicBedrockMantle
except Exception:  # pragma: no cover
    AnthropicBedrockMantle = None

from app.ai.prompt import PROMPT
from app.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_BASE_URL,
    ANTHROPIC_MODEL,
    ANTHROPIC_WORKSPACE_ID,
)

client = None
if AnthropicBedrockMantle is not None and ANTHROPIC_API_KEY:
    default_headers = None
    if ANTHROPIC_WORKSPACE_ID:
        default_headers = {"anthropic-workspace-id": ANTHROPIC_WORKSPACE_ID}

    try:
        client = AnthropicBedrockMantle(
            api_key=ANTHROPIC_API_KEY,
            base_url=ANTHROPIC_BASE_URL,
            default_headers=default_headers,
        )
    except Exception:
        traceback.print_exc()


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _image_mime_type(image_path: str) -> str:
    extension = Path(image_path).suffix.lower()
    if extension == ".png":
        return "image/png"
    if extension == ".webp":
        return "image/webp"
    return "image/jpeg"


def _clean_response(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```json"):
        text = text.replace("```json", "", 1)
    if text.startswith("```"):
        text = text.replace("```", "", 1)
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def _extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if hasattr(content, "text"):
        return str(getattr(content, "text", ""))
    if isinstance(content, dict):
        return " ".join(_extract_text(value) for value in content.values())
    if isinstance(content, list) or isinstance(content, tuple):
        return " ".join(_extract_text(item) for item in content)
    if hasattr(content, "content"):
        return _extract_text(getattr(content, "content"))
    return str(content)


def _extract_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass
    return None


def _client() -> AnthropicBedrockMantle | None:
    return client


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


def analyze_image(image_path: str) -> str | dict[str, Any]:
    client = _client()
    selected_provider = "bedrock"
    image_path_obj = Path(image_path)
    image_exists = image_path_obj.exists()
    mime_type = _image_mime_type(image_path)

    request_payload = {
        "model": ANTHROPIC_MODEL,
        "temperature": 0,
        "max_tokens": 900,
        "messages": [
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
                    {"type": "text", "text": PROMPT},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "data": _encode_image(image_path),
                            "media_type": mime_type,
                        },
                    },
                ],
            },
        ],
    }

    request_url = str(client.base_url).rstrip("/") + "/v1/messages" if client is not None else None
    print("[Bedrock] AI provider selected:", selected_provider)
    print("[Bedrock] Model name:", ANTHROPIC_MODEL)
    print("[Bedrock] Base URL:", ANTHROPIC_BASE_URL)
    print("[Bedrock] Request URL:", request_url)
    print("[Bedrock] Image path:", str(image_path_obj))
    print("[Bedrock] Image exists:", image_exists)
    print("[Bedrock] Image MIME type:", mime_type)
    print("[Bedrock] Request payload:", json.dumps(request_payload, indent=2))

    if not client:
        error_message = "Anthropic AI provider is not configured. Check ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, and ANTHROPIC_WORKSPACE_ID."
        print("[Bedrock]", error_message)
        raise AIUnavailable(error_message)

    try:
        response = client.messages.with_raw_response.create(
            model=ANTHROPIC_MODEL,
            temperature=0,
            max_tokens=900,
            messages=request_payload["messages"],
        )

        http_status = getattr(response, "status_code", None)
        request_url = getattr(response, "url", None)
        raw_body = getattr(response, "text", None)

        print("[Bedrock] Request URL:", request_url)
        print("[Bedrock] HTTP status code:", http_status)
        print("[Bedrock] Raw API response body:", raw_body)

        if raw_body is not None:
            cleaned = _clean_response(_extract_text(raw_body))
            parsed = _extract_json(cleaned)
            print("[Bedrock] Parsed response:", parsed)
            if parsed:
                return parsed
            raise ValueError("Bedrock returned a response that could not be parsed as JSON. Raw body: " + repr(raw_body))

        raise ValueError("Bedrock returned no response body. HTTP status: " + str(http_status))

    except Exception as exc:
        print("[Bedrock] Exception during analyze_image:", type(exc).__name__, repr(exc))
        traceback.print_exc()
        if hasattr(exc, "http_response"):
            http_response = getattr(exc, "http_response")
            try:
                print("[Bedrock] Exception HTTP status code:", http_response.status_code)
                print("[Bedrock] Exception raw body:", http_response.text)
            except Exception as inner_exc:
                print("[Bedrock] Failed to read exception http_response:", repr(inner_exc))
        raise


class AIUnavailable(Exception):
    pass


def generate_text(prompt: str, system_prompt: str | None = None) -> str:
    client = _client()
    if not client:
        raise AIUnavailable("Anthropic AI provider is not configured")

    prompt_text = prompt or ""
    system_text = system_prompt or "You are a helpful engineering QA/QC assistant. Respond clearly and concisely."

    request_payload = {
        "model": ANTHROPIC_MODEL,
        "temperature": 0,
        "max_tokens": 700,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": prompt_text},
        ],
    }

    request_url = str(client.base_url).rstrip("/") + "/v1/messages"
    print("[Bedrock] AI provider selected:", "bedrock")
    print("[Bedrock] Model name:", ANTHROPIC_MODEL)
    print("[Bedrock] Base URL:", ANTHROPIC_BASE_URL)
    print("[Bedrock] Request URL:", request_url)
    print("[Bedrock] Request payload:", json.dumps(request_payload, indent=2))

    if not client:
        raise AIUnavailable("Anthropic AI provider is not configured")

    try:
        response = client.messages.with_raw_response.create(
            model=ANTHROPIC_MODEL,
            temperature=0,
            max_tokens=700,
            messages=request_payload["messages"],
        )

        http_status = getattr(response, "status_code", None)
        request_url = getattr(response, "url", None)
        raw_body = getattr(response, "text", None)

        print("[Bedrock] Request URL:", request_url)
        print("[Bedrock] HTTP status code:", http_status)
        print("[Bedrock] Raw API response body:", raw_body)

        cleaned = _clean_response(_extract_text(raw_body)) if raw_body is not None else ""
        if cleaned:
            print("[Bedrock] Parsed response:", cleaned)
            return cleaned

        raise ValueError("Bedrock returned an empty or unparseable response. Raw body: " + repr(raw_body))

    except AIUnavailable:
        raise
    except Exception as exc:
        print("[Bedrock] Exception during generate_text:", type(exc).__name__, repr(exc))
        traceback.print_exc()
        if hasattr(exc, "http_response"):
            http_response = getattr(exc, "http_response")
            try:
                print("[Bedrock] Exception HTTP status code:", http_response.status_code)
                print("[Bedrock] Exception raw body:", http_response.text)
            except Exception as inner_exc:
                print("[Bedrock] Failed to read exception http_response:", repr(inner_exc))
        raise
