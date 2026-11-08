"""Create (or reset) the farm_market MySQL database with the schema and sample data.

    python init_db.py

Uses the DB_* settings from .env. WARNING: drops and recreates all farm_market tables."""
import sys

import mysql.connector

from farmmarket import config, dbinit

if __name__ == "__main__":
    try:
        n = dbinit.run_script()
    except mysql.connector.Error as exc:
        print(f"Could not set up the database: {exc.msg}\nCheck that MySQL is running and the DB_* values in .env are correct "
              f"(the user needs permission to create databases).")
        sys.exit(1)
    print(f"Database '{config.DB_NAME}' created and populated ({n} statements). Demo password for all accounts: Demo@1234")
