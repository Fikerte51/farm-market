"""Test fixtures: a throw-away MySQL database (farm_market_test) rebuilt from the real SQL script."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DB_NAME"] = "farm_market_test"

from farmmarket import auth, config, db, dbinit  # noqa: E402

config.DB_NAME = "farm_market_test"


@pytest.fixture(scope="session", autouse=True)
def _database():
    dbinit.run_script("farm_market_test")
    db.reset_pool()
    yield


@pytest.fixture()
def fresh():
    """Reset all data before the test (fast enough: the whole script runs in about a second)."""
    dbinit.run_script("farm_market_test")
    db.reset_pool()
    yield


def user(name):
    return auth.load_user(db.query_one("SELECT user_id FROM users WHERE username=%s", (name,))["user_id"])


@pytest.fixture()
def ahmed(fresh):  return user("farmer_ahmed")
@pytest.fixture()
def mariam(fresh): return user("farmer_mariam")
@pytest.fixture()
def salem(fresh):  return user("farmer_salem")
@pytest.fixture()
def dubai(fresh):  return user("buyer_dubai")
@pytest.fixture()
def adcm(fresh):   return user("buyer_adcm")
@pytest.fixture()
def admin1(fresh): return user("admin1")
