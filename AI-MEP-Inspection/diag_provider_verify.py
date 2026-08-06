import os, sys, traceback

# Verify analyze_image binding
from app.ai import provider
from app.ai.provider import analyze_image

print('analyze_image.__module__ ->', analyze_image.__module__)

# Print provider and model
from app import config
print('Provider from config:', config.AI_PROVIDER)
print('NVIDIA_MODEL:', os.getenv('NVIDIA_MODEL'))

# Call analyze_image once and print HTTP details if any
image_path = 'uploads/test-nvidia.png'
print('\nInvoking analyze_image(%r) ...' % image_path)
try:
    res = analyze_image(image_path)
    print('\nanalyze_image returned:', res)
except Exception as exc:
    print('\nException during analyze_image:')
    traceback.print_exc()
    if hasattr(exc, 'http_response'):
        http_resp = getattr(exc, 'http_response')
        try:
            print('\nException http_response.status_code:', http_resp.status_code)
            print('\nException http_response.text:')
            print(http_resp.text)
        except Exception as inner:
            print('Failed to read exception http_response:', repr(inner))
    else:
        print('\nNo http_response attribute on exception.')
    # Re-raise to avoid suppressing
    raise

print('\nDone')
