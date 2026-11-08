"""Runs database/farm_market_full.sql (schema + triggers + views + sample data) on the MySQL server.
Understands the DELIMITER lines used by the trigger definitions, so it works without the mysql command-line tool."""
import re
from pathlib import Path

import mysql.connector

from . import config

SCRIPT = config.BASE_DIR / "database" / "farm_market_full.sql"


def split_statements(text: str) -> list[str]:
    statements, buf, delim = [], [], ";"
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("DELIMITER "):
            delim = stripped.split(None, 1)[1].strip()
            continue
        if not buf and (not stripped or stripped.startswith("--")):
            continue
        buf.append(line)
        if stripped.endswith(delim):
            stmt = "\n".join(buf).rstrip()
            statements.append(stmt[: -len(delim)].rstrip())
            buf = []
    if buf and "\n".join(buf).strip():
        statements.append("\n".join(buf).strip())
    return [s for s in statements if s]


def run_script(db_name: str | None = None, script: Path = SCRIPT, user=None, password=None) -> int:
    """Execute the script. `db_name` redirects it to another database (used by the automated tests)."""
    text = script.read_text(encoding="utf-8")
    if db_name and db_name != "farm_market":
        text = re.sub(r"\bfarm_market\b", db_name, text)
    conn = mysql.connector.connect(host=config.DB_HOST, port=config.DB_PORT,
                                   user=user or config.DB_USER, password=password if password is not None else config.DB_PASSWORD,
                                   autocommit=True)
    cur = conn.cursor()
    count = 0
    try:
        for stmt in split_statements(text):
            cur.execute(stmt)
            count += 1
            try:
                cur.fetchall()
            except mysql.connector.Error:
                pass
    finally:
        cur.close()
        conn.close()
    return count
