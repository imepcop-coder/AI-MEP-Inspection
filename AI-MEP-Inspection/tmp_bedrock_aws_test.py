from app.config import ANTHROPIC_BASE_URL
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(api_key=None, base_url=ANTHROPIC_BASE_URL, aws_region='us-east-1')
print('Using AWS auth, client created')
try:
    resp = client.messages.with_raw_response.create(
        model='anthropic.claude-sonnet-4-20250514-v1:0',
        temperature=0,
        max_tokens=5,
        messages=[
            {'role': 'system', 'content': 'You are helpful.'},
            {'role': 'user', 'content': 'Hello?'}
        ]
    )
    print('status', getattr(resp,'status_code',None))
    print('text', getattr(resp,'text',None))
except Exception as e:
    import traceback
    traceback.print_exc()
