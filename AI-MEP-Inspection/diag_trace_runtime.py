"""
Trace the runtime analyze_image import and execution path.
- Creates uploads/test-trace.png (1x1 PNG)
- Prints AI_PROVIDER, NVIDIA_MODEL, presence of NVIDIA_API_KEY and ANTHROPIC_API_KEY
- Shows which modules are pre-imported and which modules are imported during the analyze_image call
- Calls app.ai.provider.analyze_image and prints any stdout already emitted by the provider
- Prints the exact function/module being executed and full Python traceback if an exception occurs

Do not modify application source. This script only creates a temporary test image file and does introspection.
"""
import os, sys, traceback, importlib, sys

# Print env/config
from app import config
print('AI_PROVIDER from config:', repr(config.AI_PROVIDER))
print('AI_PROVIDER == "nvidia"?', config.AI_PROVIDER.strip().lower() == 'nvidia')
print('NVIDIA_MODEL:', repr(os.getenv('NVIDIA_MODEL')))
print('NVIDIA_API_KEY loaded:', bool(os.getenv('NVIDIA_API_KEY')))
print('ANTHROPIC_API_KEY loaded:', bool(os.getenv('ANTHROPIC_API_KEY')))

# Pre-import modules list snapshot
pre_modules = set(sys.modules.keys())
print('\nModules loaded before analyze_image snapshot count:', len(pre_modules))

# Show if app.ai.nvidia and app.ai.bedrock are already importable
try:
    import app.ai.nvidia as ai_nvidia
    print('\napp.ai.nvidia module already importable; analyze_image:', getattr(ai_nvidia, 'analyze_image', None))
except Exception as e:
    print('\napp.ai.nvidia not importable yet:', repr(e))

try:
    import app.ai.bedrock as ai_bedrock
    print('\napp.ai.bedrock module already importable; analyze_image:', getattr(ai_bedrock, 'analyze_image', None))
except Exception as e:
    print('\napp.ai.bedrock not importable yet:', repr(e))

# Prepare a tiny 1x1 PNG image in uploads/
uploads_dir = os.path.join(os.getcwd(), 'uploads')
os.makedirs(uploads_dir, exist_ok=True)
image_path = os.path.join(uploads_dir, 'test-trace.png')
if not os.path.exists(image_path):
    # 1x1 PNG base64
    png_b64 = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII='
    import base64
    with open(image_path, 'wb') as f:
        f.write(base64.b64decode(png_b64))
    print('\nWrote test image:', image_path)
else:
    print('\nTest image already exists:', image_path)

# Now call analyze_image via provider and record module imports that occurred during the call
from app.ai import provider

# Capture modules before call
before = set(sys.modules.keys())
print('\nCalling provider.analyze_image(...) now...')

try:
    res = provider.analyze_image(image_path)
    print('\nanalyze_image returned (type={}):'.format(type(res)))
    print(res)
except Exception as exc:
    print('\nException raised during provider.analyze_image call:')
    traceback.print_exc()
    # Attempt to show http_response attribute if present
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
    # After printing full traceback, re-raise to not suppress exception
    raise
finally:
    after = set(sys.modules.keys())
    new = after - before
    print('\nModules imported during analyze_image call (new modules):')
    for m in sorted([m for m in new if m.startswith('app.ai')]):
        print(' -', m)
    # Also show which module provides the concrete analyze_image function by introspecting provider.dispatch
    # provider.analyze_image is the dispatcher function; check which module was actually called by checking sys.modules
    # Try to locate app.ai.bedrock or app.ai.nvidia in sys.modules and print their analyze_image object
    print('\nIntrospect available analyze_image functions:')
    try:
        import app.ai.bedrock as bed
        print('app.ai.bedrock.analyze_image =', bed.analyze_image)
    except Exception as e:
        print('app.ai.bedrock not loaded:', repr(e))
    try:
        import app.ai.nvidia as nvd
        print('app.ai.nvidia.analyze_image =', nvd.analyze_image)
    except Exception as e:
        print('app.ai.nvidia not loaded:', repr(e))

print('\nScript completed')
