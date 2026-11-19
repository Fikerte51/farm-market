"""Place supplied vector PDFs without rasterising their text and connectors."""
from pathlib import Path
from pypdf import PdfReader,PdfWriter,Transformation
from reportlab.platypus import Flowable


def pdf_size(path):
    b=PdfReader(path).pages[0].mediabox
    return float(b.width),float(b.height)


class VectorDiagram(Flowable):
    def __init__(self,path,max_width,max_height,placements):
        super().__init__();self.path=Path(path);self.placements=placements
        w,h=pdf_size(path);scale=min(max_width/w,max_height/h)
        self.width=w*scale;self.height=h*scale;self.hAlign='CENTER'
    def drawOn(self,canv,x,y,_sW=0):
        x+=_sW/2
        self.placements.append((canv.getPageNumber()-1,self.path,x,y,self.width,self.height))


def merge_diagrams(path,placements):
    if not placements:return
    path=Path(path);reader=PdfReader(path)
    for index,source,x,y,w,h in placements:
        p=PdfReader(source).pages[0];pw,ph=float(p.mediabox.width),float(p.mediabox.height)
        transform=Transformation().translate(-float(p.mediabox.left),-float(p.mediabox.bottom)).scale(w/pw,h/ph).translate(x,y)
        reader.pages[index].merge_transformed_page(p,transform,over=True)
    writer=PdfWriter();writer.append_pages_from_reader(reader)
    if reader.metadata:writer.add_metadata({k:str(v) for k,v in reader.metadata.items() if v is not None})
    tmp=path.with_name(path.name+'.vector-tmp');writer.write(tmp);tmp.replace(path)
