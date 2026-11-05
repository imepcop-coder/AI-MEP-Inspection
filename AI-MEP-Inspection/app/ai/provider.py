"""AI provider dispatch module.

This module selects the concrete AI implementation at import time based on the
AI_PROVIDER config and binds the module-level names `analyze_image` and `chat`
(also aliased as `generate_text`) directly to the real implementation. This
ensures `from app.ai.provider import analyze_image` yields the concrete
function (so its __module__ reflects the implementation module).

It also prints a single startup log indicating the selected provider.
"""
from __future__ import annotations

import importlib
import sys
from typing import Any

from app.config import AI_PROVIDER

provider = (AI_PROVIDER or "bedrock").strip().lower()
print(f"Using AI Provider: {provider}")


def _import_module(module_name: str):
    try:
        return importlib.import_module(module_name)
    except Exception:
        return None


# Map provider name to implementation module name
if provider == "nvidia":
    _impl = _import_module("app.ai.nvidia")
elif provider in {"bedrock", "anthropic"}:
    _impl = _import_module("app.ai.bedrock")
elif provider == "gemini":
    _impl = _import_module("app.ai.gemini")
else:
    # default to bedrock
    _impl = _import_module("app.ai.bedrock")

# Fallback: ensure some implementation is available
if _impl is None:
    # Try bedrock as last resort
    _impl = _import_module("app.ai.bedrock")

if _impl is not None and hasattr(_impl, "AIUnavailable"):
    AIUnavailable = getattr(_impl, "AIUnavailable")
else:
    class AIUnavailable(RuntimeError):
        """Raised when the selected AI provider is unavailable."""


# Bind analyze_image to the concrete implementation (or provide a clear error)
if _impl is not None and hasattr(_impl, "analyze_image"):
    analyze_image = getattr(_impl, "analyze_image")
else:
    def analyze_image(image_path: str) -> Any:  # pragma: no cover - explicit error path
        raise RuntimeError(f"No analyze_image implementation available for provider: {provider}")

# Bind chat / generate_text to concrete implementation if available
if _impl is not None:
    if hasattr(_impl, "chat"):
        chat = getattr(_impl, "chat")
    elif hasattr(_impl, "generate_text"):
        chat = getattr(_impl, "generate_text")
    else:
        def chat(*args, **kwargs):  # pragma: no cover - explicit error path
            raise RuntimeError(f"No chat/generate_text implementation available for provider: {provider}")
else:
    def chat(*args, **kwargs):  # pragma: no cover - explicit error path
        raise RuntimeError(f"No AI provider module available for provider: {provider}")

# Keep backwards compatibility for callers expecting generate_text
generate_text = chat
