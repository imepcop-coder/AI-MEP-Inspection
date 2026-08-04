from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_assistant_chat_endpoint_returns_response():
    client = TestClient(app)
    response = client.post(
        "/assistant/chat",
        data={"prompt": "Draft a concise inspection report for an HVAC QA review."},
        headers={"Origin": "http://testserver"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert payload["template"]
    assert payload["document_type"]


def test_assistant_chat_form_avoids_generic_processing_state():
    template = Path("app/templates/assistant.html").read_text(encoding="utf-8")
    ui_script = Path("app/static/js/ui.js").read_text(encoding="utf-8")

    assert 'id="chatForm"' in template
    assert 'data-skip-processing="true"' in template
    assert "form.dataset.skipProcessing === 'true'" in ui_script
