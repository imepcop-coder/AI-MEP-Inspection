from openpyxl import load_workbook
from pathlib import Path
p=Path('final/AI-MEP-Inspection/reports/upload_response2.xlsx')
wb=load_workbook(p)
ws=wb.active
imgs = getattr(ws, '_images', [])
print('Images:', len(imgs))
if imgs:
    img=imgs[0]
    print('type', type(img))
    print('has attr anchor?', hasattr(img,'anchor'))
    a=getattr(img,'anchor',None)
    print('anchor type', type(a))
    try:
        print('anchor repr', repr(a))
    except Exception as e:
        print('anchor repr error', e)
    # try attributes
    if hasattr(a,'_from'):
        f=a._from
        print('from:', dir(f))
        try:
            print('from.col', f.col, 'from.colOff', getattr(f,'colOff',None))
            print('from.row', f.row, 'from.rowOff', getattr(f,'rowOff',None))
        except Exception as e:
            print('from attr error', e)
    if hasattr(a,'_to'):
        t=a._to
        print('to:', dir(t))
        try:
            print('to.col', t.col, 'to.colOff', getattr(t,'colOff',None))
            print('to.row', t.row, 'to.rowOff', getattr(t,'rowOff',None))
        except Exception as e:
            print('to attr error', e)
    if hasattr(img,'width'):
        print('img.width', img.width, 'img.height', img.height)
