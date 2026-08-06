from app.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_WORKSPACE_ID
import httpx
import json

models = [
    'anthropic.claude-instant-1',
    'anthropic.claude-3',
    'anthropic.claude-3.1',
    'anthropic.claude-3.2',
    'anthropic.claude-4',
    'anthropic.claude-4.1',
    'anthropic.claude-4.1-mini',
    'anthropic.claude-4.1-realtime',
    'anthropic.claude-4.1-vision',
    'anthropic.claude-4-vision',
    'anthropic.claude-haiku-4-5',
    'anthropic.claude-haiku-4',
    'anthropic.claude-pro-1',
    'anthropic.claude-pro-1-realtime',
]

headers = {
    'Authorization': f'Bearer {ANTHROPIC_API_KEY}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
    'anthropic-workspace-id': ANTHROPIC_WORKSPACE_ID,
}
url = ANTHROPIC_BASE_URL.rstrip('/') + '/v1/messages'
print('URL', url)
print('Headers', {k:(v if k!='Authorization' else 'REDACTED') for k,v in headers.items()})

with httpx.Client(timeout=30) as client:
    for model in models:
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'Hello, can you answer briefly?'}
            ],
            'max_tokens': 5,
            'temperature': 0,
        }
        try:
            resp = client.post(url, json=payload, headers=headers)
            print('MODEL', model, 'STATUS', resp.status_code)
            print(resp.text[:500])
        except Exception as e:
            print('MODEL', model, 'EXCEPTION', type(e).__name__, str(e))
