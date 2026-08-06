import boto3
import json
import traceback

session = boto3.Session()
creds = session.get_credentials()
print('creds', creds)
print('region', session.region_name)
try:
    client = session.client('bedrock', region_name='us-east-1')
    print('client created', client)
    resp = client.list_models()
    print(json.dumps(resp, indent=2, default=str))
except Exception as e:
    traceback.print_exc()
