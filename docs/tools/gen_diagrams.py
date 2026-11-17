"""One connected Chen ER diagram and one connected relational schema.

Graphviz routes the relationships. A shared scene generates matching PNG and
editable Draw.io output. No reference aliases or domain variants are emitted.
"""
import html
import heapq
import json
import math
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse,Polygon,Rectangle
from matplotlib.textpath import TextPath

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from farmmarket import config,db
OUT=ROOT/'docs'
NAMES={t:''.join(w.title() for w in t.split('_')) for t in [
 'farms','crops','units','markets','users','user_farms','crop_cycles','harvest_lots',
 'harvest_lot_images','stock_movements','market_requests','allocations',
 'delivery_receipts','request_status_history','audit_log']}
REL={
 ('crop_cycles','farm_id'):'Hosts',('crop_cycles','crop_id'):'Grows',('crop_cycles','expected_unit'):'Measures forecast',
 ('harvest_lots','cycle_id'):'Yields',('harvest_lots','crop_id'):'Classifies lot',('harvest_lots','unit'):'Measures harvest',
 ('harvest_lot_images','lot_id'):'Has photo',('harvest_lot_images','uploaded_by'):'Uploads',
 ('stock_movements','lot_id'):'Has movement',('stock_movements','unit'):'Measures movement',
 ('stock_movements','user_id'):'Records movement',('stock_movements','allocation_id'):'Settles',
 ('allocations','request_id'):'Fills',('allocations','lot_id'):'Reserves',('allocations','unit'):'Measures allocation',
 ('allocations','allocated_by'):'Allocates',('market_requests','market_id'):'Places',
 ('market_requests','crop_id'):'Requests crop',('market_requests','unit'):'Measures demand',
 ('market_requests','created_by'):'Creates request',('delivery_receipts','allocation_id'):'Confirms',
 ('delivery_receipts','received_by'):'Receives',('request_status_history','request_id'):'Has history',
 ('request_status_history','changed_by'):'Changes status',('audit_log','user_id'):'Performs',
 ('users','market_id'):'Employs buyer',('user_farms','user_id'):'Has assignment',('user_farms','farm_id'):'Assigned farm'}
ATTRS={
 'farms':[('farm_id','FarmID'),('farm_name','FarmName'),('emirate','Emirate')],
 'crops':[('crop_id','CropID'),('crop_name','CropName'),('category','Category')],
 'units':[('unit_code','UnitCode'),('category','Dimension'),('to_base_factor','ConversionFactor')],
 'markets':[('market_id','MarketID'),('market_name','MarketName'),('emirate','Emirate')],
 'users':[('user_id','UserID'),('username','Username'),('role','Role')],
 'user_farms':[('user_id','UserID'),('farm_id','FarmID')],
 'crop_cycles':[('cycle_id','CycleID'),('expected_harvest_date','ExpectedOn'),('expected_quantity','ExpectedQty')],
 'harvest_lots':[('lot_id','LotID'),('quantity','Quantity'),('harvest_date','HarvestDate'),('sell_by_date','SellByDate')],
 'harvest_lot_images':[('image_id','ImageID'),('file_path','FilePath'),('caption','Caption')],
 'stock_movements':[('movement_id','MovementID'),('movement_type','MovementType'),('quantity','Quantity')],
 'market_requests':[('request_id','RequestID'),('quantity','Quantity'),('needed_by_date','NeededBy'),('status','Status')],
 'allocations':[('allocation_id','AllocationID'),('quantity','Quantity'),('status','Status')],
 'delivery_receipts':[('receipt_id','ReceiptID'),('received_quantity','ReceivedQty'),('discrepancy','Discrepancy'),('shortfall_disposition','Disposition')],
 'request_status_history':[('history_id','HistoryID'),('old_status','OldStatus'),('new_status','NewStatus')],
 'audit_log':[('audit_id','AuditID'),('action','Action'),('created_at','CreatedAt')]}


def introspect():
    cols=db.query('SELECT table_name t,column_name c,column_type ty,is_nullable n,column_key k FROM information_schema.columns WHERE table_schema=%s ORDER BY table_name,ordinal_position',(config.DB_NAME,))
    fks=db.query('SELECT table_name t,column_name c,referenced_table_name rt,referenced_column_name rc FROM information_schema.key_column_usage WHERE table_schema=%s AND referenced_table_name IS NOT NULL ORDER BY table_name,column_name',(config.DB_NAME,))
    unique=db.query("SELECT table_name t,MIN(column_name) c FROM information_schema.statistics WHERE table_schema=%s AND non_unique=0 AND index_name<>'PRIMARY' GROUP BY table_name,index_name HAVING COUNT(*)=1",(config.DB_NAME,))
    tables={}
    for c in cols:
        if not c['t'].startswith('v_'):tables.setdefault(c['t'],[]).append(c)
    assert set(tables)==set(NAMES)
    return tables,fks,{(r['t'],r['c']) for r in unique}


def layout(dot):
    result=subprocess.run(['dot','-Tjson'],input=dot,text=True,capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


def simplify(points):
    out=[]
    for p in points:
        p=tuple(p)
        if out and p==out[-1]:continue
        if len(out)>1 and ((abs(out[-2][0]-out[-1][0])<.1 and abs(out[-1][0]-p[0])<.1) or
                           (abs(out[-2][1]-out[-1][1])<.1 and abs(out[-1][1]-p[1])<.1)):
            out[-1]=p
        else:out.append(p)
    return out


class Scene:
    def __init__(self,w,h,title,legend):
        self.w=w+50;self.h=h+100;self.shift=(25,75)
        self.fig=plt.figure(figsize=(self.w/72,self.h/72));self.ax=self.fig.add_axes([0,0,1,1])
        self.ax.set_xlim(0,self.w);self.ax.set_ylim(self.h,0);self.ax.axis('off')
        self.ax.text(25,25,title,fontsize=19,fontweight='bold',color='#173c2b')
        self.ax.text(25,48,legend,fontsize=11,color='#41594c')
        self.mx=ET.Element('mxfile',host='app.diagrams.net')
        page=ET.SubElement(self.mx,'diagram',name=title,id='connected')
        graph=ET.SubElement(page,'mxGraphModel',grid='1',gridSize='10',page='1',pageWidth=str(math.ceil(self.w)),pageHeight=str(math.ceil(self.h)))
        self.root=ET.SubElement(graph,'root');ET.SubElement(self.root,'mxCell',id='0');ET.SubElement(self.root,'mxCell',id='1',parent='0')
        self.boxes={};self.serial=0
    def shifted(self,p):return (p[0]+self.shift[0],p[1]+self.shift[1])
    def shape(self,i,kind,box,label,fs=12,key=False,fill='white'):
        x,y,w,h=box;x,y=self.shifted((x,y));self.boxes[i]=(x,y,w,h)
        if kind=='ellipse':patch=Ellipse((x+w/2,y+h/2),w,h,fc=fill,ec='#40594c',lw=1.15)
        elif kind=='diamond':patch=Polygon([(x,y+h/2),(x+w/2,y),(x+w,y+h/2),(x+w/2,y+h)],fc=fill,ec='#40594c',lw=1.15)
        else:patch=Rectangle((x,y),w,h,fc=fill,ec='#40594c',lw=1.2)
        self.ax.add_patch(patch)
        self.ax.text(x+w/2,y+h/2,label,fontsize=fs,ha='center',va='center',fontweight='bold' if kind=='rectangle' else 'normal',zorder=4)
        if key:
            tw=min(w-16,len(label)*fs*.53)
            self.ax.plot([x+w/2-tw/2,x+w/2+tw/2],[y+h/2+fs*.58]*2,color='#243c2f',lw=.7,zorder=5)
        val=html.escape(label).replace('\n','<br>')
        if key:val='<u>'+val+'</u>'
        style=f'whiteSpace=wrap;html=1;align=center;verticalAlign=middle;fontSize={fs};fillColor={fill};strokeColor=#40594c;'
        style+= 'ellipse;' if kind=='ellipse' else 'rhombus;' if kind=='diamond' else 'rounded=0;fontStyle=1;'
        c=ET.SubElement(self.root,'mxCell',id=i,value=val,style=style,vertex='1',parent='1')
        ET.SubElement(c,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    def text(self,p,text,fs=10):
        x,y=self.shifted(p)
        self.ax.text(x,y,text,fontsize=fs,ha='center',va='center',zorder=5,bbox=dict(fc='white',ec='none',pad=.8))
        self.serial+=1;w=max(24,len(text)*fs*.6)
        c=ET.SubElement(self.root,'mxCell',id='label_'+str(self.serial),value=text,style=f'text;html=1;align=center;verticalAlign=middle;fillColor=#ffffff;strokeColor=none;fontSize={fs};',vertex='1',parent='1')
        ET.SubElement(c,'mxGeometry',x=str(x-w/2),y=str(y-8),width=str(w),height='16',attrib={'as':'geometry'})
    def line(self,i,source,target,points,arrow=False,color='#66786c',orthogonal=True):
        points=[self.shifted(p) for p in simplify(points)]
        self.ax.plot([p[0] for p in points],[p[1] for p in points],color=color,lw=.85,zorder=0)
        if arrow and len(points)>1:self.ax.annotate('',xy=points[-1],xytext=points[-2],arrowprops=dict(arrowstyle='-|>',lw=.9,color=color),zorder=1)
        def anchor(n,p):
            x,y,w,h=self.boxes[n]
            return min(1,max(0,(p[0]-x)/w)),min(1,max(0,(p[1]-y)/h))
        sx,sy=anchor(source,points[0]);tx,ty=anchor(target,points[-1])
        c=ET.SubElement(self.root,'mxCell',id=i,value='',style=f'edgeStyle={"orthogonalEdgeStyle" if orthogonal else "none"};rounded=0;html=1;exitX={sx};exitY={sy};exitPerimeter=0;entryX={tx};entryY={ty};entryPerimeter=0;endArrow={"block" if arrow else "none"};startArrow=none;strokeColor={color};jumpStyle=arc;',edge='1',parent='1',source=source,target=target)
        g=ET.SubElement(c,'mxGeometry',relative='1',attrib={'as':'geometry'})
        a=ET.SubElement(g,'Array',attrib={'as':'points'})
        for x,y in points[1:-1]:ET.SubElement(a,'mxPoint',x=str(x),y=str(y))
    def save(self,stem):
        self.fig.savefig(OUT/(stem+'.png'),dpi=150,bbox_inches='tight',facecolor='white')
        plt.close(self.fig)
        ET.ElementTree(self.mx).write(OUT/(stem+'.drawio'),encoding='utf-8',xml_declaration=True)


def graph_points(edge,height):
    points=next(d['points'] for d in edge['_draw_'] if d['op']=='b')
    result=[(x,height-y) for x,y in points]
    if edge.get('pos','').startswith('e,'):
        end=edge['pos'].split()[0].split(',');result.append((float(end[1]),height-float(end[2])))
    return result


def er(tables,fks,uniq):
    lines=['digraph G {','graph [rankdir=LR,splines=ortho,nodesep=.85,ranksep=.8,pad=.3,outputorder=edgesfirst];',
           'node [fontname="Helvetica"];edge [dir=none,fontname="Helvetica",fontsize=11,labeldistance=2.3,labelangle=28];']
    for t in tables:lines.append(f'{t} [shape=box,label="",style=invis,fixedsize=true,width=4.1,height=2.55];')
    for i,f in enumerate(fks):
        verb=REL[(f['t'],f['c'])]
        label=verb.replace(' ','\\n',1) if len(verb)>13 else verb
        lines.append(f'r{i} [shape=diamond,label={json.dumps(label)},fontsize=12,width=1.45,height=.8,margin=.12];')
        nullable=next(r['n']=='YES' for r in tables[f['t']] if r['c']==f['c'])
        ca='0..1' if nullable else '1';cb='0..1' if (f['t'],f['c']) in uniq else '0..N'
        lines.append(f'{f["rt"]}:e -> r{i}:w [headlabel="{ca}"];')
        lines.append(f'r{i}:e -> {f["t"]}:w [taillabel="{cb}"];')
    lines.append('}')
    data=layout('\n'.join(lines));w,h=map(float,data['bb'].split(',')[2:])
    scene=Scene(w,h,'Connected ER diagram - Farm & Market','Chen notation: rectangles = entities; diamonds = relationships; ovals = selected attributes; underlined = primary key. Labels show min..max participation.')
    objects={o['name']:o for o in data['objects']};ids={o['_gvid']:o['name'] for o in data['objects']}
    centers={name:(float(o['pos'].split(',')[0]),h-float(o['pos'].split(',')[1])) for name,o in objects.items()}
    for t in tables:
        x,y=centers[t];scene.shape(t,'rectangle',(x-95,y-23,190,46),NAMES[t],fs=14,fill='#eef5f0')
        attrs=ATTRS[t]
        offsets=[(-77,-64),(77,-64),(-77,64),(77,64)] if len(attrs)==4 else [(0,-66),(-77,64),(77,64)] if len(attrs)==3 else [(-77,-64),(77,-64)]
        for (column,label),(dx,dy) in zip(attrs,offsets):
            assert any(r['c']==column for r in tables[t])
            key=next(r['k']=='PRI' for r in tables[t] if r['c']==column)
            aid='attr_'+t+'_'+column;ox,oy=x+dx,y+dy
            scene.shape(aid,'ellipse',(ox-67,oy-18,134,36),label,fs=11,key=key)
            vx,vy=dx,dy;k=min(95/abs(vx) if vx else 1e6,23/abs(vy) if vy else 1e6)
            a=(x+vx*k,y+vy*k)
            ex,ey=x-ox,y-oy;d=math.sqrt((ex/67)**2+(ey/18)**2);b=(ox+ex/d,oy+ey/d)
            scene.line('a_'+aid,t,aid,[a,b],color='#819086',orthogonal=False)
    for i,f in enumerate(fks):
        o=objects['r'+str(i)];x,y=centers['r'+str(i)];rw=float(o['width'])*72;rh=float(o['height'])*72
        verb=REL[(f['t'],f['c'])]
        if len(verb)>13:verb=verb.replace(' ','\n',1)
        scene.shape('r'+str(i),'diamond',(x-rw/2,y-rh/2,rw,rh),verb,fs=11,fill='#fcfbf6')
    for i,e in enumerate(data['edges']):
        a,b=ids[e['tail']],ids[e['head']];pts=graph_points(e,h)
        if a in tables:
            start=pts[0];pts=[(centers[a][0]+95,centers[a][1]),(start[0],centers[a][1]),start]+pts[1:]
        if b in tables:
            end=pts[-1];pts=pts[:-1]+[end,(end[0],centers[b][1]),(centers[b][0]-95,centers[b][1])]
        scene.line('rel_edge_'+str(i),a,b,pts)
        for label,position in [('headlabel','head_lp'),('taillabel','tail_lp')]:
            if position in e:
                x,y=map(float,e[position].split(','));scene.text((x,h-y),e[label],11)
    scene.save('ER_diagram')


def route_schema(boxes,ports):
    """Orthogonal visibility-grid routing: no segment may cross table text."""
    margin=22
    xs=sorted({round(v,3) for x,y,w,h in boxes.values() for v in (x-margin,x+w+margin)})
    ys={round(v,3) for x,y,w,h in boxes.values() for v in (y-margin,y+h+margin)}
    for start,end in ports:ys.update((round(start[1],3),round(end[1],3)))
    ys=sorted(ys);xi={v:i for i,v in enumerate(xs)};yi={v:i for i,v in enumerate(ys)}
    valid={};clear={};used={};pointdirs={}
    def free(i,j):
        if (i,j) not in valid:
            x,y=xs[i],ys[j]
            valid[i,j]=not any(bx-9<x<bx+bw+9 and by-9<y<by+bh+9 for bx,by,bw,bh in boxes.values())
        return valid[i,j]
    def segment(a,b):
        key=tuple(sorted((a,b)))
        if key in clear:return clear[key]
        x1,y1=xs[a[0]],ys[a[1]];x2,y2=xs[b[0]],ys[b[1]]
        for x,y,w,h in boxes.values():
            if y1==y2:
                if y-9<y1<y+h+9 and max(min(x1,x2),x-9)<min(max(x1,x2),x+w+9):clear[key]=False;return False
            elif x-9<x1<x+w+9 and max(min(y1,y2),y-9)<min(max(y1,y2),y+h+9):clear[key]=False;return False
        clear[key]=True;return True
    results={}
    for n in sorted(range(len(ports)),key=lambda i:abs(ports[i][0][0]-ports[i][1][0])+abs(ports[i][0][1]-ports[i][1][1])):
        start,end=ports[n]
        a=(xi[round(start[0],3)],yi[round(start[1],3)]);b=(xi[round(end[0],3)],yi[round(end[1],3)])
        first=(*a,2);best={first:0};previous={};queue=[(0,0,first)];last=None
        while queue:
            _,cost,state=heapq.heappop(queue)
            if cost!=best[state]:continue
            i,j,d=state
            if (i,j)==b:last=state;break
            for ni,nj,nd in [(i-1,j,0),(i+1,j,0),(i,j-1,1),(i,j+1,1)]:
                if not(0<=ni<len(xs) and 0<=nj<len(ys)) or not free(ni,nj) or not segment((i,j),(ni,nj)):continue
                edge=tuple(sorted(((i,j),(ni,nj))))
                crossing=bool(pointdirs.get((ni,nj),set())-{nd})
                newcost=cost+abs(xs[ni]-xs[i])+abs(ys[nj]-ys[j])+(16 if d!=nd and d!=2 else 0)+100*used.get(edge,0)+(25 if crossing else 0)
                nxt=(ni,nj,nd)
                if newcost<best.get(nxt,float('inf')):
                    best[nxt]=newcost;previous[nxt]=state
                    heuristic=abs(xs[ni]-xs[b[0]])+abs(ys[nj]-ys[b[1]])
                    heapq.heappush(queue,(newcost+heuristic,newcost,nxt))
        if last is None:raise RuntimeError('No route for FK '+str(n))
        states=[last]
        while states[-1] in previous:states.append(previous[states[-1]])
        states.reverse()
        for v,z in zip(states,states[1:]):
            edge=tuple(sorted((v[:2],z[:2])));used[edge]=used.get(edge,0)+1
            pointdirs.setdefault(z[:2],set()).add(z[2])
        results[n]=[(xs[i],ys[j]) for i,j,d in states]
    return [simplify(results[i]) for i in range(len(ports))]


def schema(tables,fks,uniq):
    fkset={(f['t'],f['c']) for f in fks}
    lines=['digraph G {','graph [rankdir=BT,splines=ortho,nodesep=.85,ranksep=1.1,pad=.3];node [shape=plain,fontname="Helvetica",fontsize=12];edge [arrowsize=.6];']
    for t,rows in tables.items():
        label='<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5"><TR><TD COLSPAN="3"><B>'+t+'</B></TD></TR>'
        for r in rows:
            tags=('PK ' if r['k']=='PRI' else '')+('FK ' if (t,r['c']) in fkset else '')+('UQ ' if (t,r['c']) in uniq else '')+('NN' if r['n']=='NO' else '')
            label+=f'<TR><TD PORT="{r["c"]}" COLSPAN="3"><TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0"><TR><TD ALIGN="LEFT">{r["c"]}</TD><TD ALIGN="LEFT"> {html.escape(r["ty"].upper())} </TD><TD ALIGN="LEFT"> {tags}</TD></TR></TABLE></TD></TR>'
        lines.append(f'{t} [label=<{label}</TABLE>>];')
    for f in fks:lines.append(f'{f["t"]}:{f["c"]}:e -> {f["rt"]}:{f["rc"]}:w;')
    lines.append('}');data=layout('\n'.join(lines));w,h=map(float,data['bb'].split(',')[2:])
    scene=Scene(w,h,'Connected relational schema - Farm & Market','All 15 tables and 28 foreign keys. Arrows run from child FK to parent key. PK = primary key; FK = foreign key; UQ = unique; NN = not null. Brown = user FKs; purple = unit FKs; green = other FKs.')
    ids={o['_gvid']:o['name'] for o in data['objects']}
    boxes={}
    for o in data['objects']:
        t=o['name'];cx,cy=map(float,o['pos'].split(','));ww=float(o['width'])*72;hh=float(o['height'])*72
        x,y=cx-ww/2,h-cy-hh/2
        boxes[t]=(x,y,ww,hh)
        # Reproduce the measured HTML table in the editable source and PNG.
        scene.shape(t,'rectangle',(x,y,ww,hh),'',fill='#edf2f9')
        rowh=hh/(len(tables[t])+1)
        scene.ax.text(x+scene.shift[0]+ww/2,y+scene.shift[1]+rowh/2,t,fontsize=12,ha='center',va='center',fontweight='bold')
        scene.ax.plot([x+25,x+25+ww],[y+75+rowh]*2,color='#648172',lw=.8)
        htmlrows=['<b>'+t+'</b><hr>']
        fw=max(TextPath((0,0),r['c'],size=10).get_extents().width for r in tables[t])+14
        tw=max(TextPath((0,0),r['ty'].upper(),size=9).get_extents().width for r in tables[t])+14
        textscale=min(1,(ww-16)/(fw+tw+48))
        for j,r in enumerate(tables[t]):
            tags=('PK ' if r['k']=='PRI' else '')+('FK ' if (t,r['c']) in fkset else '')+('UQ ' if (t,r['c']) in uniq else '')+('NN' if r['n']=='NO' else '')
            yy=y+75+rowh*(j+1.5)
            scene.ax.text(x+31,yy,r['c'],fontsize=10*textscale,va='center')
            scene.ax.text(x+33+fw*textscale,yy,r['ty'].upper(),fontsize=9*textscale,va='center',color='#42594b')
            scene.ax.text(x+25+ww-6,yy,tags,fontsize=8*textscale,ha='right',va='center',color='#526b5a')
            htmlrows.append(html.escape(r['c']+' : '+r['ty'].upper()+'   '+tags)+'<br>')
        cell=scene.root.find(f"mxCell[@id='{t}']");cell.set('value',''.join(htmlrows));cell.set('style','rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=6;fontSize=11;fillColor=#edf2f9;strokeColor=#40594c;')
    ports=[];anchors=[]
    for f in fks:
        child,parent=f['t'],f['rt'];x,y,ww,hh=boxes[child];px,py,pw,ph=boxes[parent]
        ri=next(i for i,r in enumerate(tables[child]) if r['c']==f['c'])
        pi=next(i for i,r in enumerate(tables[parent]) if r['c']==f['rc'])
        cy=y+hh/(len(tables[child])+1)*(ri+1.5)
        pky=py+ph/(len(tables[parent])+1)*(pi+1.5)
        ports.append(((x+ww+22,cy),(px-22,pky)))
        anchors.append(((x+ww,cy),(px,pky)))
    for i,(f,points) in enumerate(zip(fks,route_schema(boxes,ports))):
        start,end=anchors[i]
        color='#93765b' if f['rt']=='users' else '#81719a' if f['rt']=='units' else '#547668'
        scene.line('fk_'+str(i),f['t'],f['rt'],[start]+points+[end],arrow=True,color=color)

    scene.save('relational_schema')


def main():
    tables,fks,uniq=introspect();er(tables,fks,uniq);schema(tables,fks,uniq)
    (OUT/'schema_manifest.json').write_text(json.dumps(dict(database=config.DB_NAME,table_count=len(tables),foreign_key_count=len(fks),tables=tables,foreign_keys=fks,notation='Connected Chen ER diagram and connected FK schema. No reference aliases.',relationships=[dict(f,verb=REL[(f['t'],f['c'])]) for f in fks]),indent=2))
    # These generated variants are obsolete. Keep only the two canonical pairs.
    for pattern in ['ER_diagram*.svg','relational_schema*.svg','ER_diagram_*.png','relational_schema_*.png']:
        for p in OUT.glob(pattern):p.unlink()
    print('Generated one connected ER diagram and one connected relational schema: PNG + Draw.io only.')


if __name__=='__main__':main()
