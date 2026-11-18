"""Export native poster objects for the editable presentation builder."""
import html
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from build_pdfs import DOCS,TEAM,LAB,tests
from poster_layout import build_poster


def export(path):
    texts=build_poster(DOCS,TEAM,LAB,tests())
    for t in texts:
        t['text']=html.unescape(re.sub('<[^>]+>','',t['text'].replace('<br/>','\n')))
    root=ET.parse(DOCS/'ER_diagram.drawio').getroot()
    cells={c.get('id'):c for c in root.findall('.//mxCell')}
    vertices=[];edges=[]
    def box(c):
        g=c.find('mxGeometry');return {k:float(g.get(k)) for k in ['x','y','width','height']}
    for key,c in cells.items():
        if c.get('vertex')!='1':continue
        style=c.get('style','');b=box(c)
        vertices.append(dict(id=key,box=b,text=html.unescape(re.sub('<[^>]+>','',c.get('value','').replace('<br>','\n'))),
            kind='ellipse' if 'ellipse;' in style else 'diamond' if 'rhombus;' in style else 'label' if key.startswith('label_') else 'rect',
            key='<u>' in c.get('value',''),fs=float(re.search(r'fontSize=([\d.]+)',style).group(1))))
    for key,c in cells.items():
        if c.get('edge')!='1':continue
        style=dict(p.split('=',1) for p in c.get('style').split(';') if '=' in p)
        def port(n,prefix):
            b=box(cells[c.get(n)]);return [b['x']+b['width']*float(style[prefix+'X']),b['y']+b['height']*float(style[prefix+'Y'])]
        points=[port('source','exit')]+[[float(p.get('x')),float(p.get('y'))] for p in c.findall('./mxGeometry/Array/mxPoint')]+[port('target','entry')]
        edges.append(dict(id=key,points=points))
    bounds=dict(width=max(v['box']['x']+v['box']['width'] for v in vertices)+25,
                height=max(v['box']['y']+v['box']['height'] for v in vertices)+25)
    Path(path).write_text(json.dumps(dict(texts=texts,vertices=vertices,edges=edges,bounds=bounds,
        background=str(Path(__file__).parent/'assets/poster_background.png'))))


if __name__=='__main__':export(sys.argv[1])
