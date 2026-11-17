"""Build the technical document and A1 poster from current diagrams and evidence.
Run after gen_diagrams.py, pytest --junitxml=docs/test_results.xml and the live runner.
"""
import datetime as dt
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A1,A2,A4,landscape
from reportlab.lib.styles import ParagraphStyle,getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate,Frame,Image,KeepTogether,NextPageTemplate,
    PageBreak,PageTemplate,Paragraph,Spacer,Table,TableStyle)

from submission_content import TEAM,LAB,ENTITIES,TEST_PLAN
ROOT=Path(__file__).resolve().parents[2];DOCS=ROOT/'docs'
GREEN=colors.HexColor('#246345');DARK=colors.HexColor('#173c2b');PALE=colors.HexColor('#edf5f0')
styles=getSampleStyleSheet()
body=ParagraphStyle('body',fontName='Helvetica',fontSize=9.5,leading=13,spaceAfter=6)
small=ParagraphStyle('small',parent=body,fontSize=8,leading=10,spaceAfter=3)
h1=ParagraphStyle('h1',parent=styles['Heading1'],textColor=DARK,fontSize=18,leading=22,spaceAfter=12)
h2=ParagraphStyle('h2',parent=styles['Heading2'],textColor=GREEN,fontSize=12,leading=15,spaceBefore=10,spaceAfter=6)
title=ParagraphStyle('title',parent=styles['Title'],fontSize=27,leading=31,textColor=DARK,spaceAfter=15)


def clean(text):
    return str(text).replace('\u2011','-').replace('\u2013','-').replace('\u2014',' - ').replace('\u2260','!=').replace('\u2192','->').replace('\u2022','-').replace('\u2019',"'").replace('\u2018',"'").replace('\u201c','"').replace('\u201d','"')


def P(text,style=body):return Paragraph(clean(text),style)


def plain(text,style=body):
    text=html.escape(clean(text))
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',text)
    return P(text.replace('\n','<br/>'),style)


def table(rows,widths,style=small):
    cells=[[plain(c,style) for c in r] for r in rows]
    cells[0]=[P('<font color="white"><b>'+html.escape(clean(c))+'</b></font>',style) for c in rows[0]]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),GREEN),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PALE]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#cedcd2')),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    return t


def fitted(path,w,h):
    iw,ih=PILImage.open(path).size;scale=min(w/iw,h/ih)
    return Image(str(path),width=iw*scale,height=ih*scale,hAlign='CENTER')


def tests():
    out=[]
    for tc in ET.parse(DOCS/'test_results.xml').iter('testcase'):
        status='SKIP' if tc.find('skipped') is not None else 'FAIL' if tc.find('failure') is not None or tc.find('error') is not None else 'PASS'
        out.append(dict(area=tc.get('classname','').split('.')[-1].replace('test_',''),name=tc.get('name',''),status=status))
    return out


def footer(c,doc):
    w,h=c._pagesize
    c.setStrokeColor(colors.HexColor('#c8d7cd'));c.line(16*mm,14*mm,w-16*mm,14*mm)
    c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#53685b'))
    c.drawString(16*mm,10*mm,'COSC444 | Farm & Market | Lab '+LAB)
    c.drawRightString(w-16*mm,10*mm,str(doc.page))


def technical():
    live=json.loads((DOCS/'live_assistant_validation.json').read_text())
    manifest=json.loads((DOCS/'schema_manifest.json').read_text())
    evidence=tests()
    doc=BaseDocTemplate(str(DOCS/'Technical_Document.pdf'),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,
        topMargin=17*mm,bottomMargin=20*mm,title='Farm & Market - Technical Document',author='; '.join(n for n,_ in TEAM))
    def template(name,size):
        w,h=size
        return PageTemplate(id=name,pagesize=size,frames=[Frame(18*mm,20*mm,w-36*mm,h-37*mm,id=name+'frame',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=footer)
    doc.addPageTemplates([template('portrait',A4),template('diagram',landscape(A2))])
    width=A4[0]-36*mm
    s=[Spacer(1,12*mm),P('Local Farm & Market<br/>Food Availability System',title),P('COSC444 Database Systems | Khalifa University',h2),
       P('Technical document - lab section '+LAB),table([['Team member','Student ID']]+TEAM,[width*.67,width*.33]),Spacer(1,10*mm),
       P('1. Purpose and architecture',h1),
       P('Farmers record crop plans, harvests and supply allocations; market buyers discover available produce, place requests and confirm receipts. Administrators maintain reference data, users, audit records and analytics. All seed data is fictional.'),
       table([['Layer','Responsibility'],['Streamlit GUI','Role menus, validated forms, stock tables, photos, charts and assistant chat.'],
        ['Python services','Ownership checks and one atomic database transaction per action.'],['MySQL 8','15 base tables, 28 foreign keys, views, CHECK/UNIQUE constraints and append-only/stock guard triggers.'],
        ['LangChain + Gemini','Six read-only, role-scoped data tools plus clarification and decline tools; supporting records are displayed. Gemini uses v1beta for function calling.']],[width*.25,width*.75]),
       P('Security and audit',h2),P('Passwords are bcrypt hashes. Five failed sign-ins trigger a five-minute lock; idle sessions expire after 30 minutes. Server-side permissions enforce farm assignment and market ownership. Failed attempts and denied access are audited.'),
       PageBreak(),P('2. Entity justification',h1),P('Each entity represents a separate identity, event or relationship. The association table user_farms resolves a many-to-many relationship; allocations resolves lot-to-request supply.'),
       table([['Entity','Why it exists']]+ENTITIES,[width*.29,width*.71]),
       P('Cardinality and normalisation',h2),P('A required foreign key gives each child exactly one parent, while a nullable FK permits zero or one. A parent may have zero or many children unless a UNIQUE FK limits it to zero or one. For example, an allocation has at most one receipt. User_farms has a composite key; neither user_id nor farm_id is unique alone.'),
       P('Request status history versus audit log',h2),P('Request_status_history is a business timeline for a specific request. Audit_log is a security and operational record across the application, including failures that do not produce a request transition. Keeping them separate avoids forcing unrelated security events into a business lifecycle.')]
    for prefix,section in [('ER_diagram','3. Connected ER diagram'),('relational_schema','4. Connected relational schema')]:
        note=('Chen notation follows the classroom convention: each entity appears once as a rectangle, its selected attributes are ovals, and named relationship diamonds connect the actual entities. Primary keys are underlined; the relational schema below lists all implemented columns.' if prefix=='ER_diagram' else 'Every table appears once. Orthogonal FK connectors link child fields directly to their referenced parent keys. Arrows point to the parent. Brown = user FKs; purple = unit FKs; green = other FKs. PK = primary key; FK = foreign key; UQ = unique; NN = not null.')
        s.extend([NextPageTemplate('diagram'),PageBreak(),P(section,h1),P(note,small),
            P('The model contains 15 entities/tables and 28 implemented relationships. In the ER diagram, 1 means exactly one, 0..1 optional one, and 0..N optional many. The unique allocation FK limits each allocation to at most one receipt.',small),
            fitted(DOCS/(prefix+'.png'),landscape(A2)[0]-36*mm,landscape(A2)[1]-67*mm)])
    s.extend([NextPageTemplate('portrait'),PageBreak(),P('5. Relationship register',h1),
        P(f"All {manifest['foreign_key_count']} foreign keys from the MySQL catalogue are represented in both diagram sources. Each diagram has one PNG and one editable, single-page Draw.io source."),
        table([['Child FK','Parent key','Relationship']]+[[f["t"]+'.'+f['c'],f['rt']+'.'+f['rc'],f['verb']] for f in manifest['relationships']],[width*.36,width*.34,width*.30]),
        PageBreak(),P('6. Stock, shortfalls and transactions',h1),
        P('Stock is derived, not stored: on hand = harvest additions + positive corrections - deliveries - losses - negative corrections. Reserved = reservations - releases - deliveries. Available = on hand - reserved. Forecasts in crop_cycles never contribute to physical stock.'),
        P('Delivery disposition',h2),P('A short receipt requires a reason and an explicit choice. LOST_IN_TRANSIT covers damaged, wilted, missing or otherwise unsaleable produce. RETURNED_TO_FARM is allowed only after the missing quantity is physically back at the farm and fit for sale; unverified returns must not be offered again.'),
        table([['40 kg allocated; 35 kg received','Ledger settlement','Effect on available'],['Lost/damaged 5 kg','DELIVERY 35; RESERVATION_RELEASED 5; LOSS 5','No increase from the missing 5 kg.'],['Confirmed saleable return 5 kg','DELIVERY 35; RESERVATION_RELEASED 5','Available increases by 5 kg.'],['Exactly 40 kg received','DELIVERY 40; disposition NONE','No release and no loss.']],[width*.33,width*.40,width*.27]),
        P('The receipt, delivery, release, optional loss, allocation closure, request transition and audit event commit in one transaction. The lot is locked before stock movements are written, so a concurrent allocator cannot see the intermediate released quantity. A failure rolls back all settlement records.'),
        P('Corrected sample data and existing installations',h2),P('Lot 1 now records 5 kg damaged in transit as LOSS; available stock is 0 kg. Lot 11 records the additional 2 kg wilted on arrival as LOSS; its remaining available stock is 5 kg. The 2 kg under-weight shortfall for lot 7 is also conservatively recorded as lost, because no saleable return was confirmed.'),
        P('Run upgrade_delivery_shortfalls.py for an existing database before starting the updated app. It adds the disposition column, appends missing historical LOSS movements and updates the receipt view without rewriting or deleting the ledger. Historical shortfalls without an explicit return record are classified as lost. The upgrade is idempotent and fails rather than overdrawing stock if historical quantities have already been reallocated. New installations use the corrected combined SQL script.'),
        P('Other enforced rules',h2),P('Allocation locks/rechecks the lot and demand balance; the database trigger blocks stock overdraw even for direct SQL. Farmer operations require farm ownership; buyer operations require market ownership. Units convert only within their documented dimension. Image rows store a safe relative path and metadata; JPG/PNG files remain on disk and missing files produce a warning.'),
        PageBreak(),P('7. Test plan',h1),P('The plan lists valid, invalid, boundary and concurrent cases for every major function. The coverage column distinguishes executed automated checks from additional planned/manual stress cases; a plan is not a claim that every listed scenario has already run.')])
    for function,valid,invalid,boundary,concurrent,coverage in TEST_PLAN:
        s.extend([KeepTogether([P(function,h2),table([['Case class','Planned cases'],['Valid',valid],['Invalid',invalid],['Boundary',boundary],['Concurrent',concurrent],['Coverage',coverage]],[width*.19,width*.81])]),Spacer(1,4)])
    counts={}
    for row in evidence:
        area=counts.setdefault(row['area'],dict(PASS=0,FAIL=0,SKIP=0));area[row['status']]+=1
    s.extend([PageBreak(),P('8. Executed automated results',h1),
        P('Offline regression tests use a separate farm_market_test database rebuilt from the same SQL. Gemini is replaced only in the offline assistant cases; the tool layer, permissions and database queries remain real.'),
        table([['Area','Passed','Failed','Skipped']]+[[a,str(v['PASS']),str(v['FAIL']),str(v['SKIP'])] for a,v in counts.items()],[width*.55,width*.15,width*.15,width*.15]),
        P('Command: python -m pytest tests -k "not test_live_gemini_roundtrip" -q --junitxml=docs/test_results.xml',small),
        P('The separate live evidence below supplies twelve actual Gemini questions rather than treating scripted responses as live validation.'),
        table([['#','Test case','Actual']]+[[str(i),r['area']+': '+re.sub(r'^test_','',r['name']).replace('_',' '),r['status']] for i,r in enumerate(evidence,1)],[width*.05,width*.84,width*.11]),
        PageBreak(),P('9. Live Gemini answers versus SQL',h1),
        P('Run: '+live['run_at']+' (Asia/Dubai). Model: '+live['model']+'; API: '+live['api_version']+'. Dataset: a freshly seeded farm_market_live_validation database, separate from both the working database and the offline test schema.'),
        P('Every question below made a real Gemini call. The primary model reached its daily quota after ten verified cases; the remaining cases use Gemini 3.5 Flash-Lite with the same key. Each answer is labelled with its model. The answer is recorded as returned (Markdown formatting rendered for readability); SQL expectations are independent queries. Clarification, role denial and unavailable data intentionally have no SQL result. Unsafe write/credential requests remain blocked before the model and are covered by the offline suite.'),
        P('Reproduce with: python docs/tools/validate_live_assistant.py. Raw answers, tool calls, SQL, returned rows and timings are stored in docs/live_assistant_validation.json.',small)])
    for r in live['results']:
        block_start=len(s)
        s.extend([P(f"Q{r['number']:02}. {r['question']}",h2),plain(f"Role/account: {r['role']} / {r['username']} | Model: {r.get('model',live['model'])} | Real Gemini calls: {r['gemini_invocations']} | Result: {'PASS' if r['passed'] else 'FAIL'}",small),
            P('Actual assistant answer',small),plain(r['answer']),P('Independent SQL / expected result',small)])
        if r['sql']:
            s.append(plain(r['sql'],small))
            rows=r['sql_result']
            if rows:
                keys=list(rows[0]);s.append(table([keys]+[[str(row[k]) for k in keys] for row in rows],[width/len(keys)]*len(keys)))
            else:s.append(P('No rows. The request belongs to a different market.',small))
        else:s.append(plain(r['verification'],small))
        s.extend([plain('Verification: '+r['verification']+'. Tool calls: '+', '.join(r['tools_called']),small),Spacer(1,8)])
        block=s[block_start:];del s[block_start:];s.append(KeepTogether(block))
    s.extend([P('10. Reproducibility and limitations',h1),
        P('Install requirements and MySQL 8; copy .env.example to .env and configure local credentials. For a new disposable demo database run python init_db.py; this resets demo records. For an existing database use the non-destructive upgrade instead. Start with streamlit run app.py. The demo password is Demo@1234.'),
        P('The assistant needs internet access and a Gemini API key and is subject to model quotas. The validator paces calls, preserves verified answers and reports failures rather than fabricating success. Sessions are server-memory demo sessions. A returned-to-farm declaration is a user attestation, not an automated quality inspection. Backups require both MySQL and the image/upload folders.')])
    doc.build(s)


def poster():
    live=json.loads((DOCS/'live_assistant_validation.json').read_text());results=tests()
    W,H=landscape(A1);c=canvas.Canvas(str(DOCS/'Poster.pdf'),pagesize=(W,H))
    c.setTitle('Farm & Market - COSC444 Poster');c.setAuthor('; '.join(n for n,_ in TEAM))
    c.setFillColor(DARK);c.rect(0,H-73*mm,W,73*mm,fill=1,stroke=0)
    c.setFillColor(colors.white);c.setFont('Helvetica-Bold',40);c.drawString(15*mm,H-23*mm,'LOCAL FARM & MARKET')
    c.setFont('Helvetica',19);c.drawString(15*mm,H-35*mm,'Food availability, accountable stock and safe fulfilment')
    c.setFont('Helvetica',12);c.drawString(15*mm,H-46*mm,'COSC444 Database Systems | Khalifa University | Lab B1 | Synthetic educational data')
    c.setFont('Helvetica',11)
    c.drawString(15*mm,H-56*mm,'Ahmed Hassen Mohammed - 100064745  |  Rewan Ramadan - 100064842')
    c.drawString(15*mm,H-64*mm,'Lara Al-Omari - 100064797  |  Fikertemariam Aklilu - 100064744')
    margin=15*mm;gap=12*mm;left=margin;right=W/2+gap/2;cw=(W-2*margin-gap)/2;top=H-88*mm
    def textblock(x,y,w,heading,text,fs=13):
        p=P(heading,ParagraphStyle('posterh',parent=h1,fontSize=19,leading=23));_,h=p.wrap(w,1000);p.drawOn(c,x,y-h);y-=h+5*mm
        p=plain(text,ParagraphStyle('posterp',parent=body,fontSize=fs,leading=fs*1.35));_,h=p.wrap(w,2000);p.drawOn(c,x,y-h);return y-h-9*mm
    def picture(path,x,y,w,maxh):
        iw,ih=PILImage.open(path).size;h=min(maxh,w*ih/iw);ww=h*iw/ih
        c.drawImage(str(path),x+(w-ww)/2,y-h,width=ww,height=h,mask='auto');return y-h-6*mm
    y=textblock(left,top,cw,'One database, three workspaces','Farmers publish harvests and allocate supply; buyers search, request and confirm receipts; admins manage reference data, users and analytics. Python + Streamlit + MySQL 8 + LangChain / Google Gemini.')
    y=textblock(left,y,cw,'ER model: all 15 entities and 28 relationships','Entities are connected through relationship diamonds, with oval attributes and underlined primary keys. Users and Units link to the records that reference them; cardinalities appear beside the relationship diamonds.',12)
    y=picture(DOCS/'ER_diagram.png',left,y,cw,270*mm)
    y=textblock(left,y,cw,'Safe shortfalls, no damaged produce for sale','A 5 kg damaged shortfall releases its reservation and records LOSS 5 in the same transaction. Only a physically returned, fit-for-sale quantity becomes available again. The receipt retains the reason and disposition.',13)
    textblock(left,y,cw,'Stock and security','Stock comes from an append-only movement ledger. Row locks and database triggers prevent overselling. bcrypt, login lock-out, role ownership and append-only audit provide accountability.',12)
    y=textblock(right,top,cw,'Relational schema: exact FK endpoints','PK/FK/UQ/NN and data types come from the MySQL catalogue. Direct orthogonal connectors link child foreign keys to parent keys. Each table is shown once in a single connected model. Brown connectors refer to Users; purple connectors refer to Units; green connectors show the remaining foreign keys.',12)
    y=picture(DOCS/'relational_schema.png',right,y,cw,315*mm)
    passed=sum(r['status']=='PASS' for r in results);livepass=sum(r['passed'] for r in live['results'])
    y=textblock(right,y,cw,'Measured validation',f'{passed} automated tests pass against real MySQL. Coverage includes valid/invalid inputs, boundaries, ownership, rollback, 10 simultaneous allocations and delivery-loss races. A documented plan covers every major function.',13)
    y=textblock(right,y,cw,'12 real Gemini questions',f'{livepass}/12 live questions verified on a separate synthetic database. Actual answers sit beside independent SQL results in the technical document. Ambiguity, role denial and unavailable prices are included; unsafe writes are blocked before the model.',13)
    textblock(right,y,cw,'Reproduce the demo','python init_db.py (new disposable demo only)\nstreamlit run app.py\nExisting databases: python upgrade_delivery_shortfalls.py\nEvidence: docs/test_results.xml and docs/live_assistant_validation.json',11)
    c.setFont('Helvetica',9);c.setFillColor(colors.HexColor('#53685b'));c.drawString(margin,8*mm,'A1 landscape | One PNG and editable Draw.io source supplied per diagram | All example data fictional')
    c.showPage();c.save()


if __name__=='__main__':
    technical();poster();print('Technical document and poster written to',DOCS)
