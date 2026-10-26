import os, sys
repo_app_path = os.path.join(os.getcwd(), 'final', 'AI-MEP-Inspection')
if repo_app_path not in sys.path:
    sys.path.insert(0, repo_app_path)
from app.utils.xlsx_export import build_calculator_workbook
inputs={'flow':12,'pressure':2}
results={'outflow':10,'efficiency':'75%'}
wb = build_calculator_workbook('Pump Calculation', inputs, results, page={'formula':'Q=AV'}, project_name='Test Project')
out_path = os.path.join(repo_app_path, 'reports', 'calc_test.xlsx')
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, 'wb') as f:
    f.write(wb.read())
print('Wrote', out_path)
