from app.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_WORKSPACE_ID, ANTHROPIC_MODEL
import httpx
print('model', ANTHROPIC_MODEL)
url = ANTHROPIC_BASE_URL.rstrip('/') + '/v1/messages'
headers = {
    'Authorization': f'Bearer {ANTHROPIC_API_KEY}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
    'anthropic-workspace-id': ANTHROPIC_WORKSPACE_ID,
}
payload = {
    'model': ANTHROPIC_MODEL,
    'messages': [
        {'role': 'system', 'content': 'You are helpful.'},
        {'role': 'user', 'content': 'Hello?'}
    ],
    'max_tokens': 5,
    'temperature': 0,
}
resp = httpx.post(url, json=payload, headers=headers, timeout=30)
print('status', resp.status_code)
print(resp.text)
