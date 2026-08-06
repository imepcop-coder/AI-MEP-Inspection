"""
Usage: python diag_analyze_run.py /absolute/path/to/sample.jpg

This script prints runtime AI config (AI_PROVIDER, NVIDIA_MODEL, whether NVIDIA_API_KEY is loaded),
then calls the application's analyze_image dispatch (app.ai.provider.analyze_image) with the
provided image path. It prints any stdout emitted by the provider (bedrock prints request URL/status/raw body)
and, if an exception occurs, prints the full Python traceback. If the exception carries an
http_response attribute, its status code and text are also printed.

Do NOT commit this script. Run it in the same Python environment the app uses.
"""
import os
import sys
import traceback

if len(sys.argv) < 2:
    print("Usage: python diag_analyze_run.py <path-to-image>")
    sys.exit(2)

image_path = sys.argv[1]

# Print configured provider and NVIDIA env vars
from app import config
print('AI_PROVIDER from config:', repr(config.AI_PROVIDER))
print('AI_PROVIDER == "nvidia"? ', config.AI_PROVIDER.strip().lower() == 'nvidia')

nvidia_model = os.getenv('NVIDIA_MODEL')
print('NVIDIA_MODEL:', repr(nvidia_model))
print('NVIDIA_API_KEY loaded:', bool(os.getenv('NVIDIA_API_KEY')))

print('\nInvoking app.ai.provider.analyze_image("%s")' % image_path)
try:
    from app.ai import provider
    res = provider.analyze_image(image_path)
    print('\nanalyze_image returned (type={}):'.format(type(res)))
    print(res)
except Exception as exc:
    print('\nException raised during analyze_image:')
    traceback.print_exc()
    # If exception contains http_response (some SDKs attach it), print details
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
    sys.exit(1)

print('\nDone.')
