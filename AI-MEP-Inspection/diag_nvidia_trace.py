"""
Trace the NVIDIA provider path only: import app.ai.nvidia and call its analyze_image.
Do NOT import or call the Bedrock implementation.
"""
import os, sys, traceback
from app import config

print('AI_PROVIDER from config:', repr(config.AI_PROVIDER))
print('AI_PROVIDER == "nvidia"?', config.AI_PROVIDER.strip().lower() == 'nvidia')
print('NVIDIA_MODEL:', repr(os.getenv('NVIDIA_MODEL')))
print('NVIDIA_API_KEY loaded:', bool(os.getenv('NVIDIA_API_KEY')))
print('ANTHROPIC_API_KEY loaded:', bool(os.getenv('ANTHROPIC_API_KEY')))

# Ensure we do not import bedrock anywhere
print('\nAttempting to import app.ai.nvidia only...')
try:
    import importlib
    nvid = importlib.import_module('app.ai.nvidia')
    print('Imported module:', nvid)
    print('nvidia.analyze_image =', getattr(nvid, 'analyze_image', None))
except Exception as e:
    print('Failed to import app.ai.nvidia:', repr(e))
    traceback.print_exc()
    sys.exit(1)

# Create a small test file path (no need for actual image existence; we want to observe how nvidia.analyze_image behaves)
test_image = 'uploads/test-nvidia.png'

print('\nCalling app.ai.nvidia.analyze_image(%r)...' % test_image)
try:
    result = nvid.analyze_image(test_image)
    print('\nResult:', result)
except Exception as exc:
    print('\nException raised from app.ai.nvidia.analyze_image:')
    traceback.print_exc()
    # Print http_response if present
    if hasattr(exc, 'http_response'):
        http_resp = getattr(exc, 'http_response')
        try:
            print('\nException http_response.status_code:', http_resp.status_code)
            print('\nException http_response.text:')
            print(http_resp.text)
        except Exception as inner:
            print('\nFailed to read exception http_response:', repr(inner))
    else:
        print('\nNo http_response attribute on exception.')
    # Do not suppress; re-raise to satisfy "Do not suppress exceptions"
    raise

print('\nDone')
