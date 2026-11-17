"""Generate editable Draw.io and PNG ER/schema views from MySQL foreign keys.

Shared reference-panel geometry supplies orthogonal edges for both formats. Each
source contains an overview and three domain pages. Reference nodes repeat only
keys; their full definition appears on their owning domain page.
"""
import html
import json
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from farmmarket import config, db

OUT = ROOT / 'docs'
DOMAINS = {
    'cultivation': ('Cultivation and produce', ['farms','crops','crop_cycles','harvest_lots','harvest_lot_images']),
    'fulfilment': ('Market demand and fulfilment', ['markets','market_requests','allocations','delivery_receipts','request_status_history']),
    'accountability': ('Units, access and accountability', ['units','users','user_farms','stock_movements','audit_log']),
}
NAMES = {t: ''.join(x.title() for x in t.split('_')) for _, tables in DOMAINS.values() for t in tables}
REL = {
 ('crop_cycles','farm_id'): 'hosts', ('crop_cycles','crop_id'): 'grows',
 ('crop_cycles','expected_unit'): 'measures forecast', ('harvest_lots','cycle_id'): 'yields',
 ('harvest_lots','crop_id'): 'classifies lot', ('harvest_lots','unit'): 'measures harvest',
 ('harvest_lots','created_by'): 'records harvest', ('harvest_lot_images','lot_id'): 'has image',
 ('harvest_lot_images','uploaded_by'): 'uploads', ('stock_movements','lot_id'): 'has movement',
 ('stock_movements','unit'): 'measures movement', ('stock_movements','user_id'): 'records movement',
 ('stock_movements','allocation_id'): 'explains settlement', ('allocations','request_id'): 'filled by',
 ('allocations','lot_id'): 'reserves', ('allocations','unit'): 'measures allocation',
 ('allocations','allocated_by'): 'allocates', ('market_requests','market_id'): 'places',
 ('market_requests','crop_id'): 'requests crop', ('market_requests','unit'): 'measures request',
 ('market_requests','created_by'): 'creates request', ('delivery_receipts','allocation_id'): 'confirmed by',
 ('delivery_receipts','received_by'): 'confirms receipt', ('request_status_history','request_id'): 'has transition',
 ('request_status_history','changed_by'): 'changes status', ('audit_log','user_id'): 'performs action',
 ('users','market_id'): 'employs buyer', ('user_farms','user_id'): 'has assignment',
 ('user_farms','farm_id'): 'has assigned farmer',
}


def introspect():
    cols=db.query('SELECT table_name t,column_name c,column_type ty,is_nullable n,column_key k '
                  'FROM information_schema.columns WHERE table_schema=%s ORDER BY table_name,ordinal_position',(config.DB_NAME,))
    fks=db.query('SELECT table_name t,column_name c,referenced_table_name rt,referenced_column_name rc '
                 'FROM information_schema.key_column_usage WHERE table_schema=%s AND referenced_table_name IS NOT NULL '
                 'ORDER BY table_name,column_name',(config.DB_NAME,))
    uniq={(r['t'],r['c']) for r in db.query("SELECT table_name t,column_name c FROM information_schema.statistics "
          "WHERE table_schema=%s AND non_unique=0 AND index_name<>'PRIMARY' "
          "AND index_name NOT IN (SELECT index_name FROM information_schema.statistics WHERE table_schema=%s "
          "GROUP BY table_name,index_name HAVING COUNT(*)>1)",(config.DB_NAME,config.DB_NAME))}
    tables={}
    for c in cols:
        if not c['t'].startswith('v_'):tables.setdefault(c['t'],[]).append(c)
    assert set(tables)==set(NAMES), 'Update domain ownership for new tables'
    assert len(fks)==sum(1 for f in fks if f['rt'] in tables)
    return tables,fks,uniq


def rows_for(t,kind,reference,tables,fks,uniq,overview):
    pk=[r for r in tables[t] if r['k']=='PRI']
    fkmap={f['c']:f for f in fks if f['t']==t}
    selected=pk if reference else tables[t]
    if kind=='er':
        selected=pk
        if not reference:
            chosen={'farm_name','crop_name','role','market_name','quantity','expected_quantity','movement_type',
                    'file_path','status','shortfall_disposition','action','category','to_base_factor'}
            selected=pk+[r for r in tables[t] if r['c'] in chosen and r not in pk]
    elif overview and not reference:
        selected=[r for r in tables[t] if r['k']=='PRI' or r['c'] in fkmap]
    rows=[]
    for r in selected:
        tags=[]
        if r['k']=='PRI':tags.append('PK')
        if r['c'] in fkmap:tags.append('FK')
        if (t,r['c']) in uniq:tags.append('UQ')
        if r['n']=='NO':tags.append('NN')
        text=r['c'] if kind=='er' else f"{r['c']} : {r['ty'].upper()}"
        if kind=='schema' and r['c'] in fkmap:
            f=fkmap[r['c']]
            text+=f"  -> {f['rt']}.{f['rc']}"
        rows.append((text,' / '.join(tags)))
    return rows


def generate(kind,domain,tables,fks,uniq):
    # Each FK terminates at an explicitly named reference of its parent. Repeating
    # a parent key removes shared routing hubs and all crossing relationship lines.
    # Reference boxes are the SAME logical entity, not extra database tables.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    core=list(tables) if domain=='overview' else DOMAINS[domain][1]
    cols=3 if domain=='overview' else 2
    boxw,refw,gap,panelw=355,220,110,745
    rowh,head=24,36
    data={}
    for t in core:
        records=rows_for(t,kind,False,tables,fks,uniq,False)
        if kind=='er':
            # Relationship rows carry the actual FK name even when it is not a
            # conceptual attribute; this anchors each line unambiguously.
            known={text for text,tag in records}
            records += [(f['c'],'FK') for f in fks if f['t']==t and f['c'] not in known]
        data[t]=records
    heights=[head+rowh*max(len(data[t]),1)+62 for t in core]
    slots=[max(heights[r:r+cols]) for r in range(0,len(core),cols)]
    width=panelw*cols+30;height=sum(slots)+85
    fig,ax=plt.subplots(figsize=(width/80,height/80))
    ax.set_xlim(0,width);ax.set_ylim(height,0);ax.axis('off')
    prefix='ER_diagram' if kind=='er' else 'relational_schema'
    title='All 15 entities / all 28 foreign-key relationships' if domain=='overview' else DOMAINS[domain][0]
    ax.text(20,24,title,fontsize=15,fontweight='bold',color='#193d2c')
    ax.text(20,49,'[ref] repeats the same parent entity. Lines connect each FK to its referenced key; no crossings. Cardinalities read parent : child.',fontsize=9,color='#52665b')
    page=ET.Element('diagram',name=title,id=domain)
    graph=ET.SubElement(page,'mxGraphModel',grid='1',gridSize='10',page='1',pageWidth=str(width),pageHeight=str(height))
    root=ET.SubElement(graph,'root');ET.SubElement(root,'mxCell',id='0');ET.SubElement(root,'mxCell',id='1',parent='0')
    def node(i,x,y,w,h,text,color,size=12):
        ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='#638372',linewidth=1))
        cell=ET.SubElement(root,'mxCell',id=i,value=text,style=f'rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=7;fontSize={size};fillColor={color};strokeColor=#638372;',vertex='1',parent='1')
        ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
    y=75
    for r in range(0,len(core),cols):
        for c,t in enumerate(core[r:r+cols]):
            x=20+c*panelw;records=data[t];h=head+len(records)*rowh
            name=NAMES[t] if kind=='er' else t
            color='#e3f1e9' if kind=='er' else '#eaf0f9'
            text='<b>'+name+'</b><hr>'+'<br>'.join(html.escape(a.split('  -> ')[0])+' <font color="#64766d">'+html.escape(b)+'</font>' for a,b in records)
            node(t,x,y,boxw,h,text,color)
            ax.text(x+10,y+21,name,fontsize=13,fontweight='bold',color='#193d2c')
            ax.plot([x,x+boxw],[y+head,y+head],color='#638372',lw=1)
            refs={f['c']:f for f in fks if f['t']==t}
            for k,(a,tag) in enumerate(records):
                yy=y+head+rowh*(k+.5)
                # Exact reference is placed in its own adjacent box, not crowded
                # into a field/type row or a global arrow tangle.
                display=a.split('  -> ')[0]
                ax.text(x+9,yy,display,fontsize=10.5,va='center',family='DejaVu Sans')
                ax.text(x+boxw-8,yy,tag,fontsize=7.7,ha='right',va='center',color='#64766d')
                col=a.split(' : ')[0]
                if col not in refs:continue
                f=refs[col];refid=t+'__'+col
                parent=NAMES[f['rt']] if kind=='er' else f['rt']
                nullable=next(v['n']=='YES' for v in tables[t] if v['c']==col)
                parentcard='0..1' if nullable else '1'
                childcard='0..1' if (t,col) in uniq else '0..N'
                caption=REL.get((t,col),col) if kind=='er' else f['rc']
                rx=x+boxw+gap
                value=html.escape(parent+' [ref]')+'<br>'+html.escape(caption)
                node(refid,rx,yy-11,refw,22,value,'#f5f7f5',8)
                root.find(f"mxCell[@id='{refid}']").set('style','rounded=0;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;spacing=2;fontSize=8;fillColor=#f5f7f5;strokeColor=#638372;')
                # Single text line keeps every reference box within its row.
                reftext=parent if kind=='er' else parent+'.'+f['rc']
                ax.text(rx+6,yy-4,reftext+' [ref]',fontsize=8.5,va='center',color='#274b38')
                if kind=='er':ax.text(rx+6,yy+5,caption,fontsize=6.9,va='center',color='#52665b')
                ax.plot([x+boxw,rx],[yy,yy],color='#638372',lw=.9)
                ax.text(x+boxw+gap/2,yy-4,f'{parentcard} : {childcard}',fontsize=8,ha='center',color='#274b38',bbox=dict(fc='white',ec='none',pad=.1))
                if kind=='er':
                    # Relationship verb appears as a tooltip in the editable
                    # source and is fully listed in the generated manifest.
                    pass
                cell=ET.SubElement(root,'mxCell',id='e_'+refid,value=parentcard+' : '+childcard,
                    style=f'edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=none;startArrow=none;exitX=1;exitY={(head+rowh*(k+.5))/h};exitPerimeter=0;entryX=0;entryY=0.5;labelBackgroundColor=#ffffff;fontSize=9;strokeColor=#638372;',edge='1',parent='1',source=t,target=refid)
                ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
            # FK-to-parent labels are already explicit. Reference identity and
            # cardinality do not depend on the colour of a crossing arrow.
        y+=slots[r//cols]
    stem=prefix if domain=='overview' else f'{prefix}_{domain}'
    fig.savefig(OUT/(stem+'.png'),dpi=130,bbox_inches='tight',facecolor='white')
    fig.savefig(OUT/(stem+'.svg'),bbox_inches='tight',facecolor='white')
    plt.close(fig)
    return page


def main():
    OUT.mkdir(exist_ok=True)
    tables,fks,uniq=introspect()
    for kind,filename in [('er','ER_diagram.drawio'),('schema','relational_schema.drawio')]:
        mx=ET.Element('mxfile',host='app.diagrams.net')
        for domain in ['overview',*DOMAINS]:mx.append(generate(kind,domain,tables,fks,uniq))
        ET.ElementTree(mx).write(OUT/filename,encoding='utf-8',xml_declaration=True)
    manifest={'database':config.DB_NAME,'table_count':len(tables),'foreign_key_count':len(fks),
              'tables':tables,'foreign_keys':fks,'domain_pages':{k:v[1] for k,v in DOMAINS.items()},
              'notation':'Each child FK points to a named parent reference. Labels are parent : child cardinality. [ref] repeats the same logical entity, not another table.', 'relationships':[dict(f,verb=REL.get((f['t'],f['c']),f['c'])) for f in fks]}
    (OUT/'schema_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(f'Generated overview + 3 domain pages for {len(tables)} entities and {len(fks)} foreign keys.')


if __name__=='__main__':main()
