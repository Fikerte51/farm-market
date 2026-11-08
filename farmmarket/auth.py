"""Secure login: bcrypt-hashed passwords, lock-out after repeated failures, audit of every
sign-in / sign-out, password rules."""
import re

import bcrypt

from . import config, db
from .core import User, log_event
from .errors import UserError

_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-timing", bcrypt.gensalt(rounds=10))


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def validate_password(password: str) -> None:
    if not isinstance(password, str) or len(password) < 8:
        raise UserError("The password must be at least 8 characters long.")
    if len(password.encode("utf-8")) > 72:
        raise UserError("The password is too long (maximum 72 bytes).")
    if not (re.search(r"[a-z]", password) and re.search(r"[A-Z]", password) and re.search(r"\d", password)):
        raise UserError("The password must contain an uppercase letter, a lowercase letter and a digit.")


def _check(password: str, hashed: str | None) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), (hashed or "").encode("ascii") if hashed else _DUMMY_HASH)
    except (ValueError, TypeError):
        return False


def _to_user(row: dict) -> User:
    return User(user_id=row["user_id"], username=row["username"], full_name=row["full_name"], role=row["role"],
                market_id=row["market_id"], market_name=row.get("market_name"))


def load_user(user_id: int) -> User | None:
    """Fresh copy of an ACTIVE user (called on every page load so deactivation takes effect at once)."""
    row = db.query_one("SELECT u.*, m.market_name FROM users u LEFT JOIN markets m ON m.market_id=u.market_id "
                       "WHERE u.user_id=%s AND u.is_active=1", (user_id,))
    return _to_user(row) if row else None


def login(username: str, password: str) -> User:
    username = (username or "").strip()
    if not username or not password:
        raise UserError("Please enter your username and password.")
    outcome, message, user = "fail", "Invalid username or password.", None
    with db.transaction() as cur:
        cur.execute("SELECT u.*, m.market_name, (u.locked_until IS NOT NULL AND u.locked_until > NOW()) AS is_locked, "
                    "GREATEST(CEIL(TIMESTAMPDIFF(SECOND, NOW(), u.locked_until)/60), 1) AS minutes_left "
                    "FROM users u LEFT JOIN markets m ON m.market_id=u.market_id WHERE u.username=%s FOR UPDATE", (username,))
        u = cur.fetchone()
        password_ok = _check(password, u["password_hash"] if u else None)
        if u is None:
            log_event(cur, None, "LOGIN_FAILED", "users", None, f"unknown username '{username[:40]}'", False)
        elif not u["is_active"]:
            message = "This account is not active. Please contact an administrator."
            log_event(cur, None, "LOGIN_FAILED", "users", u["user_id"], f"inactive account '{username}'", False)
        elif u["is_locked"]:
            message = f"This account is temporarily locked. Try again in about {int(u['minutes_left'])} minute(s)."
            log_event(cur, None, "LOGIN_BLOCKED", "users", u["user_id"], f"locked account '{username}'", False)
        elif not password_ok:
            attempts = u["failed_attempts"] + 1
            if attempts >= config.LOCK_AFTER_FAILURES:
                cur.execute("UPDATE users SET failed_attempts=0, locked_until=NOW() + INTERVAL %s MINUTE WHERE user_id=%s",
                            (config.LOCK_MINUTES, u["user_id"]))
                log_event(cur, None, "ACCOUNT_LOCKED", "users", u["user_id"],
                          f"{config.LOCK_AFTER_FAILURES} failed logins for '{username}'", False)
                message = f"Too many failed attempts. The account is locked for {config.LOCK_MINUTES} minutes."
            else:
                cur.execute("UPDATE users SET failed_attempts=%s WHERE user_id=%s", (attempts, u["user_id"]))
                log_event(cur, None, "LOGIN_FAILED", "users", u["user_id"], f"wrong password for '{username}'", False)
                message = f"Invalid username or password. {config.LOCK_AFTER_FAILURES - attempts} attempt(s) left."
        else:
            cur.execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE user_id=%s", (u["user_id"],))
            user = _to_user(u)
            log_event(cur, user, "LOGIN_SUCCESS", "users", u["user_id"], "")
            outcome = "ok"
    if outcome != "ok":
        raise UserError(message)   # raised after the transaction so the failure counters and audit rows are kept
    return user


def logout(user: User, reason: str = "user") -> None:
    with db.transaction() as cur:
        log_event(cur, user, "SESSION_EXPIRED" if reason == "expired" else "LOGOUT", "users", user.user_id, "")


def change_password(user: User, old_password: str, new_password: str) -> None:
    validate_password(new_password)
    with db.transaction() as cur:
        cur.execute("SELECT password_hash FROM users WHERE user_id=%s FOR UPDATE", (user.user_id,))
        row = cur.fetchone()
        if not row or not _check(old_password or "", row["password_hash"]):
            log_event(cur, user, "PASSWORD_CHANGE_FAILED", "users", user.user_id, "wrong current password", False)
            ok = False
        else:
            cur.execute("UPDATE users SET password_hash=%s WHERE user_id=%s", (hash_password(new_password), user.user_id))
            log_event(cur, user, "PASSWORD_CHANGED", "users", user.user_id, "")
            ok = True
    if not ok:
        raise UserError("The current password is not correct.")
