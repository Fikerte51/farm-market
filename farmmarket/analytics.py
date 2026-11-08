"""Administrator analytics: three SQL-based analyses with filters. Mass units are converted to kg
through the units table; count units (crates) are excluded because they cannot be converted."""
from dataclasses import dataclass
from datetime import date

from . import db
from .core import User, require_role, today


@dataclass
class Filters:
    crop: str | None = None
    emirate: str | None = None
    date_from: date | None = None
    date_to: date | None = None


def _num(v) -> float:
    return float(v or 0)


def supply_vs_demand(user: User, f: Filters) -> list[dict]:
    """1) Available (unreserved, unexpired) stock vs unmet demand of open requests, kg."""
    require_role(user, "admin", "view analytics")
    sup_c, sup_p = ["d.is_active=1", "d.available>0.0005", "(d.sell_by_date IS NULL OR d.sell_by_date>=%s)"], [today()]
    dem_c, dem_p = ["r.status IN ('SUBMITTED','PARTIALLY_ALLOCATED','ALLOCATED','PARTIALLY_FULFILLED')"], []
    if f.crop:
        sup_c.append("d.crop_name=%s"); sup_p.append(f.crop)
        dem_c.append("r.crop_name=%s"); dem_p.append(f.crop)
    if f.emirate:
        sup_c.append("d.emirate=%s"); sup_p.append(f.emirate)
        dem_c.append("r.market_emirate=%s"); dem_p.append(f.emirate)
    if f.date_from:
        sup_c.append("d.harvest_date>=%s"); sup_p.append(f.date_from)
        dem_c.append("r.needed_by_date>=%s"); dem_p.append(f.date_from)
    if f.date_to:
        sup_c.append("d.harvest_date<=%s"); sup_p.append(f.date_to)
        dem_c.append("r.needed_by_date<=%s"); dem_p.append(f.date_to)
    sql = ("SELECT crop_name, emirate, ROUND(SUM(supply),1) AS supply_kg, ROUND(SUM(demand),1) AS demand_kg, "
           "ROUND(SUM(supply)-SUM(demand),1) AS gap_kg, "
           "CASE WHEN ROUND(SUM(supply)-SUM(demand),1)>0 THEN 'Surplus' WHEN ROUND(SUM(supply)-SUM(demand),1)<0 THEN 'Shortfall' ELSE 'Balanced' END AS status "
           "FROM ("
           " SELECT d.crop_name, d.emirate, d.available*u.to_base_factor AS supply, 0 AS demand FROM v_lot_details d"
           "  JOIN units u ON u.unit_code=d.unit AND u.category='mass' WHERE " + " AND ".join(sup_c) +
           " UNION ALL"
           " SELECT r.crop_name, r.market_emirate, 0, r.remaining_need*u.to_base_factor FROM v_request_summary r"
           "  JOIN units u ON u.unit_code=r.unit AND u.category='mass' WHERE " + " AND ".join(dem_c) +
           ") x GROUP BY crop_name, emirate ORDER BY crop_name, emirate")
    return db.query(sql, sup_p + dem_p)


def fulfilment(user: User, f: Filters) -> list[dict]:
    """2) Per request: requested, allocated, received, discrepancy (received - allocated) and fulfilment %."""
    require_role(user, "admin", "view analytics")
    conds, params = ["r.status<>'CANCELLED'"], []
    if f.crop:
        conds.append("r.crop_name=%s"); params.append(f.crop)
    if f.emirate:
        conds.append("r.market_emirate=%s"); params.append(f.emirate)
    if f.date_from:
        conds.append("DATE(r.created_at)>=%s"); params.append(f.date_from)
    if f.date_to:
        conds.append("DATE(r.created_at)<=%s"); params.append(f.date_to)
    sql = ("SELECT r.request_id, r.market_name, r.market_emirate AS emirate, r.crop_name, r.status, "
           " ROUND(r.requested*u.to_base_factor,1) AS requested_kg, "
           " ROUND((SELECT COALESCE(SUM(a.quantity*ua.to_base_factor),0) FROM allocations a JOIN units ua ON ua.unit_code=a.unit "
           "        WHERE a.request_id=r.request_id AND a.status IN ('ACTIVE','DELIVERED')),1) AS allocated_kg, "
           " ROUND(r.received*u.to_base_factor,1) AS received_kg, "
           " ROUND((SELECT COALESCE(SUM(v.discrepancy*uv.to_base_factor),0) FROM v_receipts v JOIN units uv ON uv.unit_code=v.unit "
           "        WHERE v.request_id=r.request_id),1) AS discrepancy_kg, "
           " ROUND(100*r.received/r.requested,1) AS fulfilment_pct "
           "FROM v_request_summary r JOIN units u ON u.unit_code=r.unit AND u.category='mass' WHERE " +
           " AND ".join(conds) + " ORDER BY r.request_id")
    return db.query(sql, params)


def loss_by_crop(user: User, f: Filters) -> list[dict]:
    """3a) Loss rate per crop: LOSS movements versus HARVEST_ADDED movements, kg."""
    require_role(user, "admin", "view analytics")
    conds, params = ["m.movement_type IN ('HARVEST_ADDED','LOSS')"], []
    if f.crop:
        conds.append("m.crop_name=%s"); params.append(f.crop)
    if f.emirate:
        conds.append("m.emirate=%s"); params.append(f.emirate)
    if f.date_from:
        conds.append("DATE(m.movement_date)>=%s"); params.append(f.date_from)
    if f.date_to:
        conds.append("DATE(m.movement_date)<=%s"); params.append(f.date_to)
    sql = ("SELECT crop_name, ROUND(harvested,1) AS harvested_kg, ROUND(lost,1) AS lost_kg, "
           "ROUND(IF(harvested>0, 100*lost/harvested, 0),1) AS loss_rate_pct FROM ("
           " SELECT m.crop_name, SUM(CASE WHEN m.movement_type='HARVEST_ADDED' THEN m.quantity*u.to_base_factor ELSE 0 END) AS harvested,"
           "  SUM(CASE WHEN m.movement_type='LOSS' THEN m.quantity*u.to_base_factor ELSE 0 END) AS lost"
           " FROM v_movements m JOIN units u ON u.unit_code=m.unit AND u.category='mass' WHERE " + " AND ".join(conds) +
           " GROUP BY m.crop_name) t ORDER BY crop_name")
    return db.query(sql, params)


def ageing(user: User, f: Filters) -> list[dict]:
    """3b) Ageing of unreserved stock by days left to the sell-by date."""
    require_role(user, "admin", "view analytics")
    t = today()
    conds, params = ["d.is_active=1", "d.available>0.0005"], []
    if f.crop:
        conds.append("d.crop_name=%s"); params.append(f.crop)
    if f.emirate:
        conds.append("d.emirate=%s"); params.append(f.emirate)
    if f.date_from:
        conds.append("d.harvest_date>=%s"); params.append(f.date_from)
    if f.date_to:
        conds.append("d.harvest_date<=%s"); params.append(f.date_to)
    sql = ("SELECT bucket, ROUND(SUM(kg),1) AS stock_kg, COUNT(*) AS `lots` FROM ("
           " SELECT d.available*u.to_base_factor AS kg, CASE "
           "  WHEN d.sell_by_date IS NULL THEN '5. No sell-by date' WHEN d.sell_by_date < %s THEN '1. Expired' "
           "  WHEN DATEDIFF(d.sell_by_date, %s) <= 2 THEN '2. Expires in 0-2 days' "
           "  WHEN DATEDIFF(d.sell_by_date, %s) <= 7 THEN '3. Expires in 3-7 days' ELSE '4. Expires in 8+ days' END AS bucket "
           " FROM v_lot_details d JOIN units u ON u.unit_code=d.unit AND u.category='mass' WHERE " + " AND ".join(conds) +
           ") x GROUP BY bucket ORDER BY bucket")
    return db.query(sql, [t, t, t] + params)


def summary(sd: list[dict], ful: list[dict], loss: list[dict]) -> dict:
    s = lambda rows, k: sum(_num(r[k]) for r in rows)
    req, rec, harv, lost = s(ful, "requested_kg"), s(ful, "received_kg"), s(loss, "harvested_kg"), s(loss, "lost_kg")
    return {
        "Available supply (kg)": round(s(sd, "supply_kg"), 1),
        "Unmet demand (kg)": round(s(sd, "demand_kg"), 1),
        "Overall fulfilment (%)": round(100 * rec / req, 1) if req else 0.0,
        "Net delivery discrepancy (kg)": round(s(ful, "discrepancy_kg"), 1),
        "Loss rate (%)": round(100 * lost / harv, 1) if harv else 0.0,
    }
