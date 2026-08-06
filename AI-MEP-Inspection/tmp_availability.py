import json, subprocess
cmd = ['aws', 'bedrock', 'list-foundation-models', '--region', 'us-east-1', '--query', "modelSummaries[?contains(providerName, 'Anthropic')].[modelId,modelName,inputModalities]", '--output', 'json']
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print('ERROR listing models', result.stderr)
    raise SystemExit(1)
models = json.loads(result.stdout)
for model_id, model_name, inputs in models:
    cmd = ['aws', 'bedrock', 'get-foundation-model-availability', '--region', 'us-east-1', '--model-id', model_id, '--output', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print('ERROR', model_id, result.stderr)
        continue
    status = json.loads(result.stdout)
    print(model_id, model_name, inputs, 'auth', status.get('authorizationStatus'), 'entitlement', status.get('entitlementAvailability'), 'region', status.get('regionAvailability'))
