"""Reviewed prose and test plan shared by the submission PDF generator."""
TEAM=[('Ahmed Hassen Mohammed','100064745'),('Rewan Ramadan','100064842'),('Lara Al-Omari','100064797'),('Fikertemariam Aklilu','100064744')]
LAB='B1'
ENTITIES=[
 ('farms','Identifies each production location and its emirate. Farm identity is separate from farmer accounts because a farm may have several assigned users.'),
 ('crops','Maintains one controlled crop vocabulary for cycles, lots and requests; prevents inconsistent free-text names and enables crop-level reporting.'),
 ('units','Stores the dimension and documented conversion factor for each unit. Every quantity refers to it; mass and count cannot be silently mixed.'),
 ('markets','Represents the buying organisation independently of its users, allowing multiple buyer accounts to share the same requests and receipts.'),
 ('users','Stores login identity, bcrypt hash, role, activation and lock-out state. Transaction FKs identify the accountable person rather than storing their name repeatedly.'),
 ('user_farms','Resolves the many-to-many assignment of farmers to farms. Its composite primary key prevents duplicate assignments.'),
 ('crop_cycles','Stores a crop-growing plan, planting date and expected harvest. Forecast quantity is deliberately separate from harvested stock.'),
 ('harvest_lots','Tracks a distinct physical harvest batch, crop, dates and original quantity. Its direct crop FK supports lot searches; a trigger keeps it consistent with the cycle crop.'),
 ('harvest_lot_images','Allows several photos per lot, with uploader, caption and file path. Binary images remain on disk; the database keeps their identity and ownership link.'),
 ('market_requests','Records a market\'s demand, quantity, unit, needed-by date and current lifecycle status. It can be fulfilled from several lots.'),
 ('allocations','Resolves the many-to-many supply relationship between lots and requests. Quantity and status describe a reservation, not a second copy of physical stock.'),
 ('stock_movements','Append-only physical and reservation ledger. Stock is derived from harvest, delivery, loss, correction and reservation movements, preserving why each quantity changed.'),
 ('delivery_receipts','Records what was actually received for one allocation. The unique allocation FK prevents duplicate confirmation; discrepancy and disposition distinguish saleable returns from losses.'),
 ('request_status_history','Keeps the ordered business lifecycle of each request: old state, new state, actor, time and reason. It explains how a request reached its current status.'),
 ('audit_log','Records security and cross-system actions, including failed logins and denied access. It is separate from status history because many audit events do not change a request and must survive failed transactions.'),
]
TEST_PLAN=[
 ('Authentication and sessions','Correct demo login, logout, active user reload','Unknown user, wrong password, inactive account','5th failure locks; lock expiry; 30-minute idle expiry','Competing login attempts lock the user row','Login/security tests executed; time-expiry checks are manual demo cases'),
 ('Passwords and user administration','Create account; bcrypt hash; deactivate another user','Weak/duplicate username; wrong role; self-deactivation','Password length and required character classes','Duplicate username submissions meet UNIQUE constraint','Business-rule tests; duplicate simultaneous submission is a planned DB stress case'),
 ('Farms, crops, markets and units','Add valid reference records and farmer assignments','Duplicates, invalid emirate, unauthorised reference edit','Inactive references rejected by new operations','Concurrent duplicate inserts meet UNIQUE/composite PK','Reference/permission tests; simultaneous duplicate insert is planned'),
 ('Crop cycles and forecasts','Add a valid plan; view expected harvest separately','Wrong owner, invalid crop/unit, duplicate cycle','Expected harvest ordered after planting; zero quantity rejected','Two cycle inserts cannot bypass the unique business key','Cycle/forecast tests; simultaneous duplicate cycle is planned'),
 ('Harvest and stock ledger','Record lot and HARVEST_ADDED atomically','Wrong owner, unknown unit, future harvest, crop mismatch','0 and 0.001; sell-by before harvest; large decimal','New movements and allocations lock/recheck lot stock','Harvest, validation and direct-SQL guard tests executed'),
 ('Produce search and units','Filter crop, emirate, sell-by, minimum quantity','Invalid/mixed dimensions cannot convert','Exactly available; sell-by today; kg/tonne conversion','Read committed queries; refresh after a stock transaction','Query/unit tests; UI filter spot checks executed'),
 ('Requests: create, change, close','Create demand; edit notes/date; cancel unused request','Other market, past needed-by, closed request edit','Cannot reduce below allocated + received','Row locks serialise changes; closing releases reservations','Lifecycle/ownership tests executed; edit-vs-close race is planned'),
 ('Allocations and release','Reserve from multiple lots; release with reason','Wrong crop/owner, expired lot, stock/request over-allocation','Exactly remaining stock and need; repeat submission','10 attempts for 5 kg: exactly 5 successes','Allocation/concurrency tests executed'),
 ('Delivery confirmation','Full receipt; returned-to-farm; lost-in-transit','Over-receipt, wrong buyer, missing reason/disposition, repeat','Zero received; 0.001 received; exactly allocated','Two confirmations: one receipt/loss; concurrent allocation cannot sell a loss','Delivery, rollback and race tests executed'),
 ('Losses and corrections','Loss with reason; admin approved addition/removal','No reason, wrong role, exceed unreserved stock','Remove exactly available; reserve balance unchanged','Lot lock and trigger prevent concurrent overdraw','Loss/correction/direct-SQL guard tests executed'),
 ('Images','Valid JPG/PNG upload; retrieve after reconnect; deactivate','GIF, wrong magic bytes, damaged file, wrong lot owner','Empty, over 5 MB, missing path, traversal path','Generated unique names avoid collisions','Image tests executed; simultaneous uploads are planned'),
 ('Analytics and exports','Supply/demand, fulfilment, loss/ageing; CSV/PDF','Non-admin, reversed dates, unsafe spreadsheet content','Empty data, date endpoints, crates excluded from kg','Read-only reports operate on committed rows','Analytics/export tests executed'),
 ('Assistant','Supported role-scoped records with SQL verification','Unsafe write/credential requests; unavailable key/network','Empty/501 chars, ambiguous crop, unknown data, bounded tool loop','Read-only tool queries; concurrent chats hold separate sessions','Offline suite plus 12 recorded real Gemini questions; parallel chat load is planned'),
 ('Audit and atomicity','Record actor/time/reason and status history','UPDATE/DELETE of ledger or audit rejected','Failed service saves no partial receipt/movements','Loss settlement rollback; repeat upgrade is idempotent','Append-only, transaction failure and migration tests executed'),
]
