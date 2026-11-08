# Local Farm & Market Food Availability System  (COSC444)

Python + **MySQL** + Streamlit GUI + **LangChain with Google Gemini**.
Farmers record harvests and allocate produce, market buyers search supply / request / confirm deliveries, administrators manage users and reference data.
Educational prototype - **all data is fictional**; no connection to government systems.
(The Fraunces and Work Sans fonts load from Google Fonts, so the pages look best with an internet connection.)

| Requirement | Where |
|---|---|
| Python GUI (Streamlit), parameterised SQL | `app.py`, `farmmarket/views/`, `farmmarket/*.py` |
| SQL database (MySQL 8) schema + sample data | `database/farm_market_full.sql` (also split in `01_schema.sql`, `02_seed.sql`) |
| ER diagram + relational schema (Draw.io) | `docs/ER_diagram.drawio`, `docs/relational_schema.drawio` (+ PNG) |
| Images (JPG/PNG linked to lots, survive restart) | `farmmarket/images.py`, folders `images/lots/` (samples) and `uploads/` (farmer uploads) |
| LangChain assistant (Gemini), read-only | `farmmarket/assistant.py` |
| **Advanced feature (required): Secure login & activity audit** | `farmmarket/auth.py`, `audit_log` table, *Audit log* page |
| Optional 2nd feature: analytics & reports (3 SQL analyses, 4 charts, CSV/PDF) | `farmmarket/analytics.py`, `reports.py`, *Analytics dashboard* page |
| Tests + technical document + poster | `tests/`, `docs/Technical_Document.pdf`, `docs/Poster.pdf` |

## 1. Install (one time)
1. **Python 3.10 or newer** and **MySQL 8.0 or newer** (server running; MySQL Workbench is fine too).
2. Open a terminal in this folder and create a virtual environment (recommended):
   ```
   python -m venv .venv
   .venv\Scripts\activate        (Windows)       source .venv/bin/activate   (macOS / Linux)
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in:
   * `DB_USER` / `DB_PASSWORD` - a MySQL user allowed to create databases (e.g. `root`).
   * `GOOGLE_API_KEY` - your Gemini key (https://aistudio.google.com/apikey). Without it everything works except the assistant, which says it is not configured.

## 2. Create the database
```
python init_db.py
```
This runs `database/farm_market_full.sql` (drops and recreates the `farm_market` database: tables, constraints, triggers, views and sample data).
Alternative: `mysql -u root -p < database/farm_market_full.sql` or open the file in MySQL Workbench and run it.
Sample dates are **relative to the day you run the script**, so nothing is expired on demo day; re-run it any time to reset the demo data.

## 3. Run
```
streamlit run app.py
```
Open http://localhost:8501. All demo accounts use the password **`Demo@1234`**:

| Role | Users |
|---|---|
| Admin | `admin1` |
| Farmer | `farmer_ahmed` (Al Ain Green Valley + Liwa Oasis), `farmer_mariam` (RAK Highland), `farmer_salem` (Al Dhaid Sun) |
| Market buyer | `buyer_dubai`, `buyer_adcm`, `buyer_sharjah`, `buyer_alain` |

## 4. Suggested live demo (12 minutes)
1. **Harvest + image + restart** - `farmer_ahmed` > *Harvest & stock* > record a lot > *Lot images* > upload a JPG/PNG. Stop the server (Ctrl+C), start it again, sign in, open the lot's photos: the picture is still there. (Lot 12 also has a deliberately missing file to show graceful handling.)
2. **Market search, request, partial delivery** - `buyer_dubai` > *Search local produce* > *My requests* > create a request. As `farmer_ahmed` > *Requests & allocation* > allocate. Back as the buyer > *Confirm deliveries* > receive less than allocated with a reason; see the discrepancy on the receipt.
3. **Business rule** - as the farmer try to allocate more than the lot's available quantity (clear message, nothing saved). Or *Harvest & stock > Open lot by number* with another farm's lot (denied + audited).
4. **LangChain assistant** - ask *"Which tomato lots are available?"* (supported), *"tomatoes"* (ambiguous -> clarification), *"What will tomato prices be?"* (unanswerable), *"delete all requests"* (refused).
5. **Advanced feature** - wrong password 5 times (lock-out), then `admin1` > *Audit log* (logins, denials, allocations). Optional: *Analytics dashboard* with filters and CSV/PDF export. Show an invalid input (negative quantity) -> friendly message.

## 5. Tests
```
pip install -r requirements-dev.txt
pytest tests
```
Uses a separate throw-away database `farm_market_test` (rebuilt from the SQL script; the DB user needs permission to create databases). 91 tests: stock calculations, allocation/oversell rules, partial deliveries, units, ownership, login lock-out, images, analytics, friendly errors, 10 simultaneous allocations, assistant (12 question groups incl. ambiguous / unanswerable / unsafe) and GUI flows. The assistant tests use a scripted stand-in for Gemini so they run offline; set `GOOGLE_API_KEY` to also run one live Gemini test.

## 6. How the important rules are enforced
* **Stock is never stored** - `v_lot_stock` sums the dated `stock_movements`. The ledger and the audit log are append-only (triggers). Expected harvest lives in `crop_cycles` and never counts as stock.
* **No overselling** - allocation locks the lot row (`SELECT ... FOR UPDATE`), re-checks availability, and a MySQL trigger re-checks every movement, even for direct SQL.
* **Atomic operations** - each action is one transaction; on any error nothing is saved.
* **Ownership** - farmers: only farms assigned to them; buyers: only their market; admins: reference data and approved corrections only. Refused attempts go to `audit_log`.
* **Units** - every quantity has a unit; conversion only through `units.to_base_factor` (mass <-> count is refused).
* **Assistant** - Gemini can only call 6 read-only, role-scoped tools (+ clarify / decline); it never writes SQL or data; unsafe wording is refused before reaching the model.

## 7. Troubleshooting
* *"The database is not reachable"* - start MySQL; check `DB_*` in `.env`; run `python init_db.py`.
* *`init_db.py` access denied / cannot create database* - use a MySQL user with CREATE privilege (e.g. root).
* *Assistant: "not configured" / "key was rejected"* - set a valid `GOOGLE_API_KEY` in `.env`, then restart Streamlit.
* *Locked out after wrong passwords* - wait 5 minutes, or run `python init_db.py` to reset the data.
* Port 8501 busy: `streamlit run app.py --server.port 8502`.

## 8. Regenerating the documents (optional)
`python docs/tools/gen_diagrams.py` (diagrams from the live schema) -> `pytest tests --junitxml=docs/test_results.xml` -> `python docs/tools/build_pdfs.py`.
Add your team names to `docs/Technical_Document.pdf` / `docs/Poster.pdf` (placeholders at the top) by editing `docs/tools/build_pdfs.py` and re-running it.

## Project structure
```
app.py                 Streamlit entry point (login, menus, sessions)
init_db.py             creates / resets the MySQL database
farmmarket/            config, db (pool + transactions), core (rules), farmer, buyer, admin, auth, images,
                       queries, analytics, reports, assistant (LangChain + Gemini), views/ (GUI pages)
database/              farm_market_full.sql (schema + data), 01_schema.sql, 02_seed.sql
images/lots/           sample photos           uploads/   farmer uploads
tests/                 pytest suite            docs/      diagrams, technical document, poster
```
