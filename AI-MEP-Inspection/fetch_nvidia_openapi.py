import os, requests, sys, json
key = os.getenv('NVIDIA_API_KEY')
if not key:
    print('NO_KEY')
    sys.exit(2)
url = 'https://api.nvcf.nvidia.com/openapi.json'
headers = {'Authorization': f'Bearer {key}'}
resp = requests.get(url, headers=headers, timeout=30)
print('STATUS', resp.status_code)
if resp.status_code == 200:
    # print compacted JSON to avoid huge output
    try:
        j = resp.json()
        print(json.dumps(j, indent=2)[:20000])
    except Exception:
        print(resp.text[:20000])
else:
    print(resp.text[:20000])
