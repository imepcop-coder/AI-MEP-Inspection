from openpyxl import load_workbook
from pathlib import Path
p=Path('final/AI-MEP-Inspection/reports/calc_test.xlsx')
wb=load_workbook(p)
print('Sheets:', wb.sheetnames)
ws=wb['Summary']
print('Title cell:', ws['A1'].value)
ws2=wb['Inputs']
print('Inputs headers:', [ws2['A1'].value, ws2['B1'].value])
print('Inputs sample:', ws2['A2'].value, ws2['B2'].value)
try:
    charts=wb['Charts']
    imgs=getattr(charts,'_images',[])
    print('Charts images:', len(imgs))
except Exception as e:
    print('Charts error', e)
