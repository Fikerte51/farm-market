"""Regression cases for saleable returns versus transit loss (real test database)."""
import datetime as dt
import threading
from decimal import Decimal

import pytest

from farmmarket import buyer, db, farmer
from farmmarket.errors import UserError


def stock():
    return db.query_one('SELECT on_hand,reserved,available FROM v_lot_stock WHERE lot_id=5')


def test_saleable_return_is_available(adcm):
    buyer.confirm_delivery(adcm,4,35,dt.date.today(),'5 kg returned fit for sale','RETURNED_TO_FARM')
    assert stock()==dict(on_hand=Decimal('35'),reserved=Decimal('0'),available=Decimal('35'))
    assert not db.query("SELECT 1 FROM stock_movements WHERE allocation_id=4 AND movement_type='LOSS'")


@pytest.mark.parametrize('received',[0,Decimal('0.001'),35])
def test_loss_never_increases_available_stock(adcm,received):
    buyer.confirm_delivery(adcm,4,received,dt.date.today(),'damaged in transit','LOST_IN_TRANSIT')
    assert stock()==dict(on_hand=Decimal('30'),reserved=Decimal('0'),available=Decimal('30'))
    assert db.query_one("SELECT quantity FROM stock_movements WHERE allocation_id=4 AND movement_type='LOSS'")['quantity']==40-Decimal(received)


@pytest.mark.parametrize('disposition',[None,'NONE','unknown'])
def test_shortfall_requires_explicit_disposition_and_rolls_back(adcm,disposition):
    before=stock()
    with pytest.raises(UserError,match='Choose whether'):
        buyer.confirm_delivery(adcm,4,35,dt.date.today(),'short delivery',disposition)
    assert stock()==before
    assert not db.query('SELECT 1 FROM delivery_receipts WHERE allocation_id=4')


def test_loss_failure_rolls_back_receipt_delivery_and_release(adcm,monkeypatch):
    real=buyer.add_movement
    def fail(cur,user,lot,mtype,*args,**kwargs):
        if mtype=='LOSS': raise UserError('simulated loss failure')
        return real(cur,user,lot,mtype,*args,**kwargs)
    monkeypatch.setattr(buyer,'add_movement',fail)
    before=stock()
    with pytest.raises(UserError):
        buyer.confirm_delivery(adcm,4,35,dt.date.today(),'damaged','LOST_IN_TRANSIT')
    assert stock()==before
    assert not db.query('SELECT 1 FROM delivery_receipts WHERE allocation_id=4')


def test_duplicate_concurrent_confirmations_record_one_loss(adcm):
    results=[]
    def worker():
        try:
            buyer.confirm_delivery(adcm,4,35,dt.date.today(),'damaged','LOST_IN_TRANSIT')
            results.append('ok')
        except UserError: results.append('rejected')
    threads=[threading.Thread(target=worker) for _ in range(2)]
    for t in threads:t.start()
    for t in threads:t.join()
    assert sorted(results)==['ok','rejected']
    assert len(db.query("SELECT 1 FROM stock_movements WHERE allocation_id=4 AND movement_type='LOSS'"))==1
    assert stock()['available']==Decimal('30')


def test_allocating_during_loss_settlement_cannot_sell_shortfall(ahmed,adcm):
    barrier=threading.Barrier(2);results=[]
    def settle():
        barrier.wait()
        buyer.confirm_delivery(adcm,4,35,dt.date.today(),'damaged','LOST_IN_TRANSIT')
    def allocate():
        barrier.wait()
        try:
            farmer.allocate(ahmed,8,5,31)
            results.append('oversold')
        except UserError:results.append('rejected')
    threads=[threading.Thread(target=settle),threading.Thread(target=allocate)]
    for t in threads:t.start()
    for t in threads:t.join()
    assert results==['rejected'] and stock()['available']==Decimal('30')


def test_corrected_seed_damage_is_not_available(fresh):
    assert db.query_one('SELECT available FROM v_lot_stock WHERE lot_id=1')['available']==0
    assert db.query_one('SELECT available FROM v_lot_stock WHERE lot_id=11')['available']==5
    from upgrade_delivery_shortfalls import upgrade
    before=db.query_one('SELECT COUNT(*) c FROM stock_movements')['c']
    assert upgrade()==0 and upgrade()==0
    assert db.query_one('SELECT COUNT(*) c FROM stock_movements')['c']==before


def test_upgrade_backfills_a_legacy_shortfall_without_rewriting_ledger(adcm):
    # Simulate a legacy receipt: it released a damaged shortfall as saleable stock.
    buyer.confirm_delivery(adcm,4,35,dt.date.today(),'damaged','RETURNED_TO_FARM')
    db.execute_autocommit('ALTER TABLE delivery_receipts DROP CHECK ck_rec_disposition')
    db.execute_autocommit("UPDATE delivery_receipts SET shortfall_disposition='NONE' WHERE allocation_id=4")
    before=db.query_one('SELECT COUNT(*) c FROM stock_movements')['c']
    from upgrade_delivery_shortfalls import upgrade
    assert upgrade()==1
    assert stock()['available']==Decimal('30')
    assert db.query_one('SELECT COUNT(*) c FROM stock_movements')['c']==before+1
    assert upgrade()==0
