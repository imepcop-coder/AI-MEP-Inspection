from app.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_WORKSPACE_ID
import httpx

models = [
    'anthropic.claude-sonnet-4',
    'anthropic.claude-fable-5',
    'anthropic.claude-sonnet-4-6',
    'anthropic.claude-opus-4-6',
    'anthropic.claude-opus-5',
    'anthropic.claude-opus-4-8',
    'anthropic.claude-opus-4-7',
    'anthropic.claude-sonnet-4-5',
    'anthropic.claude-sonnet-5',
    'anthropic.claude-opus-4-1',
    'anthropic.claude-opus-4-5',
    'anthropic.claude-3-haiku',
    'anthropic.claude-opus-4-1-20250805-v1',
    'anthropic.claude-opus-4-5-20251101-v1',
    'anthropic.claude-3-haiku-20240307-v1:0',
    'anthropic.claude-3-haiku-20240307-v1:0:48k',
    'anthropic.claude-3-haiku-20240307-v1:0:200k',
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
