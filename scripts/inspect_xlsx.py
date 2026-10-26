from openpyxl import load_workbook
from pathlib import Path
p=Path('final/AI-MEP-Inspection/reports/upload_response.xlsx')
print('Exists:', p.exists())
wb=load_workbook(p)
ws=wb.active
print('Sheet title:', ws.title)
imgs = getattr(ws, '_images', [])
print('Image count in active sheet:', len(imgs))
for i,im in enumerate(imgs,1):
    try:
        print(i, type(im), getattr(im, 'anchor', None), getattr(im, 'width', None), getattr(im, 'height', None))
    except Exception as e:
        print('img info error', e)
# Print header row values
header_row=5
print('Headers:')
for c in range(1, ws.max_column+1):
    print(c, ws.cell(header_row, c).value)
# Print first data row values
data_row=6
print('Data row:')
for c in range(1, ws.max_column+1):
    print(c, ws.cell(data_row, c).value)
print('Row height for data row:', ws.row_dimensions[data_row].height)
