from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
resp=client.get('/calculators/plumbing/water-demand', headers={'origin':'http://testserver','referer':'http://testserver'})
html=resp.text
i = html.find('order-lg-1')
print(html[i-200:i+400])
