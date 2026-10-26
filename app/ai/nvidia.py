import os
import base64
import json
import traceback
from pathlib import Path
from typing import Any

import requests

from app.ai.prompt import PROMPT


class AIUnavailable(Exception):
    pass


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


def analyze_image(image_path: str) -> dict[str, Any]:
    """Call NVIDIA Build chat completions endpoint (OpenAI-compatible).

    Uses the NVIDIA Build chat completions endpoint at integrate.api.nvidia.com
    with OpenAI-compatible chat payload. The uploaded image is included as a
    data URL in a user message following the official example.

    Environment variables used:
      - NVIDIA_API_KEY (required)
      - NVIDIA_MODEL (optional; default 'meta/llama-3.2-90b-vision-instruct')
      - NVIDIA_CHAT_URL (optional; default 'https://integrate.api.nvidia.com/v1/chat/completions')

    Returns parsed JSON from the NVIDIA response. Raises exceptions on network or
    parsing errors (no fallback substitution).
    """
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-90b-vision-instruct")
    NVIDIA_CHAT_URL = os.getenv("NVIDIA_CHAT_URL", "https://integrate.api.nvidia.com/v1/chat/completions")

    if not NVIDIA_API_KEY:
        raise AIUnavailable("NVIDIA provider requires NVIDIA_API_KEY to be set")

    mime = _image_mime_type(image_path)
    encoded = _encode_image(image_path)
    image_data_url = f"data:{mime};base64,{encoded}"

    messages = [
        {"role": "system", "content": "You are a senior Engineering QA/QC, HSE and Maintenance Inspector. Analyze only visible conditions. Return ONLY valid JSON. Never return markdown or explanations."},
        {"role": "user", "content": PROMPT},
        {"role": "user", "content": image_data_url},
    ]

    payload = {
        "model": NVIDIA_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 900,
    }

    request_url = NVIDIA_CHAT_URL
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    print("[NVIDIA] Request URL:", request_url)
    print("[NVIDIA] Model:", NVIDIA_MODEL)
    print("[NVIDIA] Payload keys:", list(payload.keys()))

    try:
        resp = requests.post(request_url, headers=headers, json=payload, timeout=120)
        status = getattr(resp, "status_code", None)
        text = getattr(resp, "text", None)

        print("[NVIDIA] HTTP status code:", status)
        print("[NVIDIA] Raw API response body:", text)

        if not text:
            raise ValueError("NVIDIA returned empty response body")

        return json.loads(text)

    except Exception as exc:
        print("[NVIDIA] Exception during analyze_image:", type(exc).__name__, repr(exc))
        traceback.print_exc()
        if hasattr(exc, "response") and getattr(exc, "response") is not None:
            try:
                print("[NVIDIA] Exception HTTP status code:", exc.response.status_code)
                print("[NVIDIA] Exception raw body:", exc.response.text)
            except Exception as inner:
                print("[NVIDIA] Failed to read exception response:", repr(inner))
        raise


def generate_text(prompt: str, system_prompt: str | None = None) -> str:
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    NVIDIA_MODEL = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-90b-vision-instruct")
    NVIDIA_CHAT_URL = os.getenv("NVIDIA_CHAT_URL", "https://integrate.api.nvidia.com/v1/chat/completions")

    if not NVIDIA_API_KEY:
        raise AIUnavailable("NVIDIA provider requires NVIDIA_API_KEY to be set")

    messages = [
        {"role": "system", "content": system_prompt or "You are a helpful assistant."},
        {"role": "user", "content": prompt or ""},
    ]

    payload = {
        "model": NVIDIA_MODEL,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 700,
    }

    request_url = NVIDIA_CHAT_URL
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }

    print("[NVIDIA] Chat request URL:", request_url)
    print("[NVIDIA] Chat payload keys:", list(payload.keys()))

    try:
        resp = requests.post(request_url, headers=headers, json=payload, timeout=120)
        status = getattr(resp, "status_code", None)
        text = getattr(resp, "text", None)

        print("[NVIDIA] Chat HTTP status code:", status)
        print("[NVIDIA] Chat raw body:", text)

        if not text:
            raise ValueError("NVIDIA returned empty chat response")

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text

        if isinstance(parsed, dict):
            choices = parsed.get("choices")
            if isinstance(choices, list) and choices:
                first = choices[0]
                msg = first.get("message") or first.get("content")
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, str):
                        return content
                if isinstance(msg, str):
                    return msg
            return json.dumps(parsed)

        return json.dumps(parsed)

    except Exception as exc:
        print("[NVIDIA] Exception during generate_text:", type(exc).__name__, repr(exc))
        traceback.print_exc()
        if hasattr(exc, "response") and getattr(exc, "response") is not None:
            try:
                print("[NVIDIA] Exception HTTP status code:", exc.response.status_code)
                print("[NVIDIA] Exception raw body:", exc.response.text)
            except Exception as inner:
                print("[NVIDIA] Failed to read exception response:", repr(inner))
        raise



