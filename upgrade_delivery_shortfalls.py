"""Non-destructive upgrade for existing databases; run once before the updated app.

Historical shortfalls have no confirmed saleable-return record, so they are
conservatively treated as lost. Existing movements remain append-only. Safe to rerun.
"""
from decimal import Decimal

from farmmarket import config, db
from farmmarket.dbinit import split_statements


def upgrade():
    if not db.query_one("SELECT 1 FROM information_schema.columns WHERE table_schema=%s "
                        "AND table_name='delivery_receipts' AND column_name='shortfall_disposition'", (config.DB_NAME,)):
        db.execute_autocommit("ALTER TABLE delivery_receipts ADD COLUMN shortfall_disposition "
                              "VARCHAR(24) NOT NULL DEFAULT 'NONE' AFTER discrepancy_reason")
    # DECIMAL(12,3) has no representable negative value between -0.001 and 0.
    # Compare with zero to avoid MySQL 8.0 negative-literal coercion quirks.
    with db.transaction() as cur:
        cur.execute("SELECT d.*,a.lot_id,a.unit FROM delivery_receipts d JOIN allocations a "
                    "ON a.allocation_id=d.allocation_id WHERE d.discrepancy < 0 "
                    "AND d.shortfall_disposition='NONE' ORDER BY a.lot_id,d.receipt_id FOR UPDATE")
        receipts = cur.fetchall()
        for r in receipts:
            cur.execute("SELECT lot_id FROM harvest_lots WHERE lot_id=%s FOR UPDATE", (r['lot_id'],))
            cur.fetchone()
            cur.execute("SELECT COALESCE(SUM(quantity),0) q FROM stock_movements "
                        "WHERE allocation_id=%s AND movement_type='LOSS'", (r['allocation_id'],))
            missing = -r['discrepancy'] - cur.fetchone()['q']
            if missing > Decimal('0.0005'):
                cur.execute("INSERT INTO stock_movements (lot_id,movement_type,quantity,unit,user_id,reason,allocation_id) "
                            "VALUES (%s,'LOSS',%s,%s,%s,%s,%s)",
                            (r['lot_id'], missing, r['unit'], r['received_by'],
                             f"Historical delivery shortfall #{r['receipt_id']}: {r['discrepancy_reason']}",r['allocation_id']))
            cur.execute("UPDATE delivery_receipts SET shortfall_disposition='LOST_IN_TRANSIT' WHERE receipt_id=%s", (r['receipt_id'],))
            cur.execute("INSERT INTO audit_log (user_id,action,table_name,record_id,details) "
                        "VALUES (%s,'SHORTFALL_UPGRADED','delivery_receipts',%s,%s)",
                        (r['received_by'],str(r['receipt_id']),"Historical unconfirmed return treated as lost; original ledger retained"))
    if not db.query_one("SELECT 1 FROM information_schema.table_constraints WHERE constraint_schema=%s "
                        "AND table_name='delivery_receipts' AND constraint_name='ck_rec_disposition'", (config.DB_NAME,)):
        db.execute_autocommit("ALTER TABLE delivery_receipts ADD CONSTRAINT ck_rec_disposition CHECK "
                              "((discrepancy=0 AND shortfall_disposition='NONE') OR "
                              "(discrepancy < 0 AND shortfall_disposition IN ('RETURNED_TO_FARM','LOST_IN_TRANSIT')))")
    schema = (config.BASE_DIR/'database/01_schema.sql').read_text()
    view = next(s for s in split_statements(schema) if s.startswith('CREATE VIEW v_receipts AS'))
    db.execute_autocommit(view.replace('CREATE VIEW','CREATE OR REPLACE VIEW',1))
    return len(receipts)


if __name__ == '__main__':
    print(f'Upgraded {upgrade()} historical shortfalls in {config.DB_NAME}; existing data preserved.')
