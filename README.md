# Local Farm & Market Food Availability System

A Python application using Streamlit, MySQL and LangChain with Google Gemini for farmers, market buyers and administrators.

## Setup

Requires Python 3.10+ and a running MySQL 8.0+ server.

From the project folder, create a virtual environment:

```bash
python -m venv .venv
```

Activate it using `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1` in Windows PowerShell, then install dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and enter your MySQL connection settings (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`). Set `GOOGLE_API_KEY` to enable the assistant.

## Database

For a new installation, create the schema and sample records:

```bash
python init_db.py
```

This recreates the `farm_market` database. Run it during initial setup, not on every startup. The MySQL account needs permission to create the database.

For an existing older database, use `python upgrade_delivery_shortfalls.py` instead.

## Run

```bash
python -m streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). Press `Ctrl+C` in the terminal to stop the app.

Included accounts use the password `Demo@1234`:

| Role | Accounts |
|---|---|
| Administrator | `admin1` |
| Farmer | `farmer_ahmed`, `farmer_mariam`, `farmer_salem` |
| Market buyer | `buyer_dubai`, `buyer_adcm`, `buyer_sharjah`, `buyer_alain` |

## File locations

| Location | Contents |
|---|---|
| `app.py` | Application entry point |
| `farmmarket/` | Interfaces, business logic, database access and assistant |
| `database/` | Combined setup script `farm_market_full.sql`, plus separate schema and seed scripts |
| `images/lots/`, `uploads/` | Sample images and uploaded images; MySQL stores their paths |
| `docs/` | ER and relational diagrams, technical document, poster PDF and editable PowerPoint |
