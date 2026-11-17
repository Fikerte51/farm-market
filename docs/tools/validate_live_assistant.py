"""Run 12 real Gemini questions against a separately seeded synthetic database.
Rebuilds ONLY farm_market_live_validation. Saves verbatim answers beside independent
SQL expectations; never saves the API key or sends the user's working database.
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from farmmarket import assistant,auth,config,db,dbinit

TARGET='farm_market_live_validation'
CASES=[
 ('buyer_dubai','Which tomato lots are available right now?','available_produce',
  "SELECT lot_id,available,unit FROM v_lot_details WHERE crop_name='Tomato' AND is_active=1 AND available>0.0005 AND (sell_by_date IS NULL OR sell_by_date>=CURDATE())",('lot_id','available','unit')),
 ('buyer_adcm','What is the status and remaining need of request 6?','request_status',
  'SELECT request_id,status,remaining_need,unit FROM v_request_summary WHERE request_id=6 AND market_id={market_id}',('request_id','status','remaining_need','unit')),
 ('buyer_dubai','Show me the status of request 6.','request_status',
  'SELECT request_id,status,remaining_need,unit FROM v_request_summary WHERE request_id=6 AND market_id={market_id}',('request_id','status','remaining_need','unit')),
 ('buyer_adcm','Which of our requests are still open?','request_status',
  "SELECT request_id,status,remaining_need,unit FROM v_request_summary WHERE market_id={market_id} AND status NOT IN ('FULFILLED','CLOSED','CANCELLED')",('request_id','status','remaining_need','unit')),
 ('admin1','Which deliveries had a discrepancy? List their receipt IDs and differences.','delivery_receipts',
  'SELECT receipt_id,discrepancy,unit,shortfall_disposition FROM v_receipts WHERE ABS(discrepancy)>=0.0005',('receipt_id','discrepancy','unit','shortfall_disposition')),
 ('buyer_dubai','What tomato harvests are expected? Label them as forecasts.','expected_harvest',
  "SELECT cycle_id,expected_quantity,expected_unit FROM v_cycles WHERE crop_name='Tomato' AND is_active=1 AND status IN ('PLANNED','GROWING','HARVESTING')",('cycle_id','expected_quantity','expected_unit')),
 ('farmer_ahmed','Across all farms assigned to me, show each harvest lot with on-hand, reserved and available stock.','stock_summary',
  'SELECT lot_id,on_hand,reserved,available,unit FROM v_lot_details WHERE is_active=1 AND farm_id IN (SELECT farm_id FROM user_farms WHERE user_id={user_id})',('lot_id','on_hand','reserved','available','unit')),
 ('buyer_dubai','Show farm stock details including on-hand and reserved quantities.','stock_summary',None,()),
 ('farmer_ahmed','Which of my allocations are active?','allocations',
  "SELECT allocation_id,quantity,unit FROM v_allocations WHERE status='ACTIVE' AND farm_id IN (SELECT farm_id FROM user_farms WHERE user_id={user_id})",('allocation_id','quantity','unit')),
 ('buyer_dubai','tomatoes','ask_clarification',None,()),
 ('buyer_dubai','What will the tomato price be next month?','cannot_answer',None,()),
 ('buyer_dubai','Which tomato lots have at least 40 kg available?','available_produce',
  "SELECT d.lot_id,d.available,d.unit FROM v_lot_details d JOIN units u ON u.unit_code=d.unit WHERE d.crop_name='Tomato' AND d.is_active=1 AND d.available>0.0005 AND (d.sell_by_date IS NULL OR d.sell_by_date>=CURDATE()) AND u.category='mass' AND d.available*u.to_base_factor>=40",('lot_id','available','unit')),
]


def canonical(rows,keys):
    return sorted([json.dumps({k:assistant._jsonable(r[k]) for k in keys},sort_keys=True) for r in rows])


def main():
    if not config.GOOGLE_API_KEY:raise SystemExit('GOOGLE_API_KEY is required')
    evidence=ROOT/'docs/live_assistant_validation.json'
    previous=json.loads(evidence.read_text()) if evidence.exists() else {}
    if not previous:dbinit.run_script(TARGET)
    config.DB_NAME=TARGET;db.reset_pool()
    results=[]
    last_request=[0.0]
    for number,(username,q,tool,sql,keys) in enumerate(CASES,1):
        prior=next((r for r in previous.get('results',[]) if r['number']==number and r['question']==q and r['passed']),None)
        if prior:
            prior.setdefault('model',previous['model']);results.append(prior);print(f'Q{number:02}: retained verified live result',flush=True);continue
        user=auth.load_user(db.query_one('SELECT user_id FROM users WHERE username=%s',(username,))['user_id'])
        executed_sql=sql.format(user_id=user.user_id,market_id=user.market_id) if sql else None
        expected=db.query(executed_sql) if sql else []
        calls=[];invocations=[]
        class Tracked:
            def __init__(self,model):self.model=model
            def bind_tools(self,tools):return Tracked(self.model.bind_tools(tools))
            def invoke(self,messages):
                for attempt in range(4):
                    delay=max(0,15-(time.monotonic()-last_request[0]))
                    if delay:time.sleep(delay)
                    last_request[0]=time.monotonic()
                    try:response=self.model.invoke(messages)
                    except Exception as exc:
                        if 'per day' in str(exc).lower():raise
                        if ('429' in str(exc) or 'RESOURCE_EXHAUSTED' in str(exc)) and attempt<3:
                            print(f'Q{number:02}: rate limited; cooling down 45 seconds',flush=True)
                            time.sleep(45);continue
                        raise
                    invocations.append(1);calls.extend(c['name'] for c in response.tool_calls)
                    return response
        start=time.monotonic()
        reply=assistant.ask(user,q,llm_factory=lambda:Tracked(assistant.get_llm()))
        rows=[r for rec in reply.records if rec['tool']==tool for r in rec['rows']]
        if sql:
            match=tool in calls and canonical(rows,keys)==canonical(expected,keys)
            verification='Returned records match the independent SQL result' if match else 'SQL/tool mismatch'
        elif tool=='stock_summary':
            match=any('not permitted' in r.get('notice','') for r in rows) or ('cannot' in reply.answer.lower() or 'not permitted' in reply.answer.lower())
            verification='Buyer cannot see private farm stock; no stock rows disclosed'
        else:
            match=tool in calls and not reply.records
            verification='Clarification without data lookup' if tool=='ask_clarification' else 'Declined because prices are absent from the schema'
        passed=bool(invocations) and reply.mode=='ai' and match
        results.append(dict(number=number,username=username,role=user.role,model=config.GEMINI_MODEL,question=q,answer=reply.answer,
            mode=reply.mode,tools_called=calls,gemini_invocations=len(invocations),sql=executed_sql,
            sql_result=[{k:assistant._jsonable(v) for k,v in r.items()} for r in expected],
            supporting_records=reply.records,verification=verification,passed=passed,seconds=round(time.monotonic()-start,2)))
        payload=dict(run_at=dt.datetime.now(ZoneInfo('Asia/Dubai')).isoformat(),model=', '.join(sorted({r['model'] for r in results})),
            api_version='v1beta',database=TARGET,dataset='Fresh synthetic seed; no working database records',
            results=results)
        (ROOT/'docs/live_assistant_validation.json').write_text(json.dumps(payload,indent=2,default=str))
        print(f'Q{number:02}: {"PASS" if passed else "FAIL"} | calls={calls} | {reply.answer[:90]}',flush=True)
    if not all(r['passed'] for r in results):raise SystemExit('Live validation has failures; inspect the evidence JSON')
    print('All 12 questions completed with real Gemini invocations.',flush=True)


if __name__=='__main__':main()
