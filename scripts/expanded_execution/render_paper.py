"""Render each draft PDF page and a contact sheet for visual review."""
from pathlib import Path
import hashlib,json
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'output/pdf/decision-context-benchmark-draft.pdf'
dest=ROOT/'data/raw/paper-review/rendered';dest.mkdir(parents=True,exist_ok=True)
doc=pdfium.PdfDocument(str(source));thumbs=[]
for i,page in enumerate(doc):
    im=page.render(scale=1.5).to_pil();im.save(dest/f'page-{i+1:02}.png')
    im.thumbnail((300,430));thumbs.append(im)
sheet=Image.new('RGB',(900,460*((len(thumbs)+2)//3)),'#dddddd');draw=ImageDraw.Draw(sheet)
for i,im in enumerate(thumbs):
    x=(i%3)*300;y=(i//3)*460;sheet.paste(im,(x,y+20));draw.text((x+10,y+3),str(i+1),fill='black')
sheet.save(dest/'contact-sheet.png')
(dest/'render-manifest.json').write_text(json.dumps({'pdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'page_count':len(doc),'renderer':'pypdfium2 5.14.0','visually_inspected':False},indent=2)+'\n')
print(json.dumps({'pages':len(doc),'directory':str(dest)}))
