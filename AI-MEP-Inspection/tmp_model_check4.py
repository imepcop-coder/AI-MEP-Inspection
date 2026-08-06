from app.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_WORKSPACE_ID
import httpx

models = [
    'claude-haiku-4-5',
    'claude-fable-5',
    'claude-opus-5',
    'claude-opus-4-8',
    'claude-opus-4-7',
    'claude-sonnet-5',
]
headers = {
    'Authorization': f'Bearer {ANTHROPIC_API_KEY}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
    'anthropic-workspace-id': ANTHROPIC_WORKSPACE_ID,
}
url = ANTHROPIC_BASE_URL.rstrip('/') + '/v1/messages'
with httpx.Client(timeout=30) as client:
    for model in models:
        payload = {'model': model, 'messages': [{'role':'system','content':'You are a helpful assistant.'},{'role':'user','content':'Hello?'}], 'max_tokens': 5, 'temperature': 0}
        resp = client.post(url, json=payload, headers=headers)
        print('MODEL', model, 'STATUS', resp.status_code)
        print(resp.text[:200])
