from app.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_WORKSPACE_ID
import httpx
url = ANTHROPIC_BASE_URL.rstrip('/') + '/v1/messages'
headers = {
    'Authorization': f'Bearer {ANTHROPIC_API_KEY}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
    'anthropic-workspace-id': ANTHROPIC_WORKSPACE_ID,
}
for model in ['nvidia.nemotron-nano-12b-v2', 'amazon.nova-pro-v1:0', 'google.gemma-3-12b-it']:
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': 'Hi'},
            {'role': 'user', 'content': 'Hello'}
        ],
        'max_tokens': 5,
        'temperature': 0,
    }
    resp = httpx.post(url, json=payload, headers=headers, timeout=30)
    print('MODEL', model, 'STATUS', resp.status_code)
    print(resp.text[:200])
