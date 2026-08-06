import json

from app.ai import bedrock


class _BrokenCompletions:
    def create(self, *args, **kwargs):
        raise RuntimeError("provider unavailable")


class _BrokenChat:
    def __init__(self):
        self.completions = _BrokenCompletions()


class _BrokenClient:
    def __init__(self):
        self.chat = _BrokenChat()


def test_analyze_image_returns_structured_fallback_when_provider_fails(tmp_path):
    image_path = tmp_path / "sample.jpg"
    image_path.write_bytes(b"fake-image")

    bedrock.client = _BrokenClient()

    result = bedrock.analyze_image(str(image_path))
    payload = json.loads(result)

    assert payload["is_supported"] is True
    assert payload["severity"] in {"Low", "Medium", "High", "Critical"}
    assert payload["status"] == "Open"
