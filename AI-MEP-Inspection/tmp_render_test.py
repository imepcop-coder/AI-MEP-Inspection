from fastapi.templating import Jinja2Templates
from pathlib import Path

class DummyURL:
    def __init__(self):
        self.path = '/calculators/test'

class DummyRequest:
    def __init__(self):
        self.scope = {'path': '/calculators/test', 'query_string': b''}
        self.url = DummyURL()
    def url_for(self, name, **path_params):
        return '/' + path_params.get('path', '')

templates = Jinja2Templates(directory=Path('app') / 'templates')
tmpl = templates.get_template('calculators/calculator_page.html')
html = tmpl.render(request=DummyRequest(), page={'title': 'Test', 'description': 'desc'}, values={}, result=None, error=None, field_errors={})
print('render len', len(html))
print(repr(html[:120]))
