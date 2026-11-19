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
from vector_diagrams import VectorDiagram,merge_diagrams
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


def fitted(path,w,h,placements=None):
    vector=path.with_suffix('.pdf')
    if vector.is_file() and placements is not None:
        return VectorDiagram(vector,w,h,placements)
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
    vector_placements=[]
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
        note=('Chen notation follows the classroom convention: each entity appears once as a rectangle, its non-FK attributes are ovals, and named relationship diamonds connect the actual entities. Identifiers are underlined. The key-only user_farms table is represented by an Assigned to M:N relationship between Users (farmer accounts) and Farms. Units, request status history, audit records and responsible-user relationships are included. Dashed red ovals are derived attributes; blue location ovals combine component attributes. Single and double relationship lines show partial and total participation.' if prefix=='ER_diagram' else 'Every table appears once. Orthogonal FK connectors link child fields directly to their referenced parent keys. Arrows point to the parent. Connector colours identify the referenced table. PK = primary key; FK = foreign key; UQ = unique; UQ1 = composite unique; NN = not null; AI = auto-increment. The bottom panel lists CHECK constraints and triggers.')
        s.extend([NextPageTemplate('diagram'),PageBreak(),P(section,h1),P(note,small),
            P('The supplied ER contains 14 entities and 27 relationship diamonds representing the 28 foreign keys in the 15-table relational schema. Two user_farms foreign keys map to one M:N assigned-to diamond. Cardinality labels 1, N and M express relationship ratios; single/double lines distinguish partial/total participation. Each allocation has at most one receipt.',small),
            fitted(DOCS/(prefix+'.png'),landscape(A2)[0]-36*mm,landscape(A2)[1]-67*mm,vector_placements)])
    s.extend([NextPageTemplate('portrait'),PageBreak(),P('5. Relationship register',h1),
        P(f"All {manifest['foreign_key_count']} foreign keys from the MySQL catalogue are represented in the relational schema. The ER includes every table except the key-only user_farms junction, represented by an assigned-to M:N relationship. Each diagram has one editable Draw.io source, a PNG preview and a vector PDF used in the documents."),
        table([['Child FK','Parent key','Relationship']]+[[f["t"]+'.'+f['c'],f['rt']+'.'+f['rc'],f['verb']] for f in manifest['relationships']],[width*.36,width*.34,width*.30]),
        PageBreak(),P('6. Stock, shortfalls and transactions',h1),
        P('Stock is derived, not stored: on hand = harvest additions + positive corrections - deliveries - losses - negative corrections. Reserved = reservations - releases - deliveries. Available = on hand - reserved. Forecasts in crop_cycles never contribute to physical stock.'),
        P('Delivery disposition',h2),P('A short receipt requires a reason and an explicit choice. LOST_IN_TRANSIT covers damaged, wilted, missing or otherwise unsaleable produce. RETURNED_TO_FARM is allowed only after the missing quantity is physically back at the farm and fit for sale; unverified returns must not be offered again.'),
        table([['40 kg allocated; 35 kg received','Ledger settlement','Effect on available'],['Lost/damaged 5 kg','DELIVERY 35; RESERVATION_RELEASED 5; LOSS 5','No increase from the missing 5 kg.'],['Confirmed saleable return 5 kg','DELIVERY 35; RESERVATION_RELEASED 5','Available increases by 5 kg.'],['Exactly 40 kg received','DELIVERY 40; disposition NONE','No release and no loss.']],[width*.33,width*.40,width*.27]),
        P('The receipt, delivery, release, optional loss, allocation closure, request transition and audit event commit in one transaction. The lot is locked before stock movements are written, so a concurrent allocator cannot see the intermediate released quantity. A failure rolls back all settlement records.'),
        P('Corrected sample data and existing installations',h2),P('Lot 1 now records 5 kg damaged in transit as LOSS; available stock is 0 kg. Lot 11 records the additional 2 kg wilted on arrival as LOSS; its remaining available stock is 5 kg. The 2 kg under-weight shortfall for lot 7 is also conservatively recorded as lost, because no saleable return was confirmed.'),
        P('Run upgrade_delivery_shortfalls.py for an existing database before starting the updated app. It adds the disposition column, appends missing historical LOSS movements and updates the receipt view without rewriting or deleting the ledger. Historical shortfalls without an explicit return record are classified as lost. The upgrade is idempotent and fails rather than overdrawing stock if historical quantities have already been reallocated. New installations use the corrected combined SQL script. The upgrade compares the three-decimal discrepancy with zero (negative means shortfall), avoiding the reported MySQL 8.0 negative fractional literal comparison issue.'),
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
    merge_diagrams(DOCS/'Technical_Document.pdf',vector_placements)


def poster():
    from poster_layout import build_poster
    build_poster(DOCS, TEAM, LAB, tests())


if __name__=='__main__':
    technical();poster();print('Technical document and poster written to',DOCS)
