"""Export poster text and native Chen objects, including imported Draw.io styles."""
import html
import json
import math
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from build_pdfs import DOCS,TEAM,LAB,tests
from poster_layout import build_poster,ER_FRAME


def plain(value):
    return html.unescape(re.sub('<[^>]+>','',re.sub(r'<br\s*/?>','\n',value,flags=re.I)))


def export(path):
    texts=build_poster(DOCS,TEAM,LAB,tests())
    for t in texts:t['text']=plain(t['text'])
    root=ET.parse(DOCS/'ER_diagram.drawio').getroot()
    cells={c.get('id'):c for c in root.findall('.//mxCell')}
    vertices=[];edges=[];byid={}
    def style(c):return dict(s.split('=',1) for s in c.get('style','').split(';') if '=' in s)
    def box(c):
        g=c.find('mxGeometry');return {k:float(g.get(k,0)) for k in ['x','y','width','height']}
    for key,c in cells.items():
        if c.get('vertex')!='1':continue
        raw=c.get('style','');s=style(c);b=box(c)
        kind='ellipse' if raw.startswith('ellipse;') else 'diamond' if raw.startswith('rhombus;') else 'label' if raw.startswith('text;') else 'roundRect' if s.get('rounded')=='1' else 'rect'
        v=dict(id=key,box=b,text=plain(c.get('value','')),kind=kind,key='<u>' in c.get('value',''),
            fs=float(s.get('fontSize',12)),bold=bool(int(s.get('fontStyle',0))&1),italic=bool(int(s.get('fontStyle',0))&2),
            fill=s.get('fillColor','none' if kind=='label' else '#FFFFFF'),stroke=s.get('strokeColor','none' if kind=='label' else '#374151'),
            stroke_width=float(s.get('strokeWidth',1)),dashed=s.get('dashed')=='1',color=s.get('fontColor','#111111'),
            align=s.get('align','center'),valign=s.get('verticalAlign','middle'))
        vertices.append(v);byid[key]=v
    def center(v):
        b=v['box'];return b['x']+b['width']/2,b['y']+b['height']/2
    def anchor(v,towards,s,prefix):
        b=v['box'];x,y=center(v)
        if prefix+'X' in s and prefix+'Y' in s:
            return [b['x']+b['width']*float(s[prefix+'X']),b['y']+b['height']*float(s[prefix+'Y'])]
        dx,dy=towards[0]-x,towards[1]-y;a=b['width']/2;h=b['height']/2
        if dx==dy==0:return [x,y]
        if v['kind']=='ellipse':k=1/math.sqrt((dx/a)**2+(dy/h)**2)
        elif v['kind']=='diamond':k=1/(abs(dx)/a+abs(dy)/h)
        else:k=min(a/abs(dx) if dx else math.inf,h/abs(dy) if dy else math.inf)
        return [x+dx*k,y+dy*k]
    for key,c in cells.items():
        if c.get('edge')!='1':continue
        s=style(c);source=byid[c.get('source')];target=byid[c.get('target')]
        points=[[float(p.get('x')),float(p.get('y'))] for p in c.findall('./mxGeometry/Array/mxPoint')]
        points=[anchor(source,points[0] if points else center(target),s,'exit')]+points+[anchor(target,points[-1] if points else center(source),s,'entry')]
        edges.append(dict(id=key,points=points,double=s.get('shape')=='link',stroke=s.get('strokeColor','#4B5563'),stroke_width=float(s.get('strokeWidth',1.6))))
    model=root.find('.//mxGraphModel')
    bounds=dict(width=float(model.get('pageWidth')),height=float(model.get('pageHeight')))
    Path(path).write_text(json.dumps(dict(texts=texts,vertices=vertices,edges=edges,bounds=bounds,
        diagram_frame=dict(zip(['x','y','w','h'],ER_FRAME)),background=str(Path(__file__).parent/'assets/poster_background.png'))))


if __name__=='__main__':export(sys.argv[1])
