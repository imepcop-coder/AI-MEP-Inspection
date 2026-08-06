import os, traceback, sys
from app import config
print('AI_PROVIDER from config:', repr(config.AI_PROVIDER))
print('AI_PROVIDER == "nvidia"?', config.AI_PROVIDER.strip().lower()=='nvidia')
# NVIDIA env
nvidia_model = os.getenv('NVIDIA_MODEL')
nvidia_key = os.getenv('NVIDIA_API_KEY')
print('NVIDIA_MODEL:', repr(nvidia_model))
print('NVIDIA_API_KEY loaded:', bool(nvidia_key))

# Now attempt to call analyze_image
from app.ai import provider
image_path = 'uploads/does_not_matter.jpg'
print('\nCalling analyze_image via provider.analyze_image(...)')
try:
    res = provider.analyze_image(image_path)
    print('analyze_image returned:', res)
except Exception as e:
    print('\nException raised during analyze_image call:')
    traceback.print_exc()
    # attempt to print http_response if present
    if hasattr(e, 'http_response'):
        http_resp = getattr(e, 'http_response')
        try:
            print('\nException http_response.status_code:', http_resp.status_code)
            print('Exception http_response.text:')
            print(http_resp.text)
        except Exception as inner:
            print('Failed to read http_response:', inner)
    else:
        print('\nNo http_response attribute on exception.')
    sys.exit(1)
print('Done')
