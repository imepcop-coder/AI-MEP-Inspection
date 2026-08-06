from app.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_WORKSPACE_ID
import httpx

models = [
    'mantle',
    'mantle-instruct',
    'mantle-mini',
    'mantle-vision',
    'mantle-vision-instruct',
    'anthropic.mantle',
    'anthropic.mantle-vision',
    'anthropic.claude-4-vision',
    'anthropic.claude-4.1-vision-instruct',
    'anthropic.claude-4.1-vision-preview',
    'anthropic.claude-4.1-vision-instr',
    'anthropic.claude-4.1-vision-chat',
    'anthropic.claude-4-vision-instruct',
    'anthropic.claude-4-vision-chat',
    'anthropic.claude-4-vision-preview',
    'anthropic.claude-4.5',
    'anthropic.claude-4.1-vision',
    'anthropic.claude-3.5',
    'anthropic.claude-3.5-mini',
    'anthropic.claude-4.5-mini',
    'anthropic.claude-4.5-vision',
    'anthropic.claude-4.5-vision-instruct',
]
headers = {
    'Authorization': f'Bearer {ANTHROPIC_API_KEY}',
    'Content-Type': 'application/json',
    'anthropic-version': '2023-06-01',
    'anthropic-workspace-id': ANTHROPIC_WORKSPACE_ID,
}
url = ANTHROPIC_BASE_URL.rstrip('/') + '/v1/messages'
print('URL', url)
with httpx.Client(timeout=30) as client:
    for model in models:
        payload = {'model': model, 'messages': [{'role':'system','content':'You are a helpful assistant.'},{'role':'user','content':'Hello?'}], 'max_tokens': 8, 'temperature': 0}
        try:
            resp = client.post(url, json=payload, headers=headers)
            print('MODEL', model, 'STATUS', resp.status_code)
            print(resp.text[:300])
        except Exception as e:
            print('MODEL', model, 'EXCEPTION', type(e).__name__, e)
