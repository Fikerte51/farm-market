"""Exceptions shown to users, and translation of raw database errors into friendly messages."""
import logging

import mysql.connector
from mysql.connector import errorcode

log = logging.getLogger("farmmarket")


class UserError(Exception):
    """A problem the user can understand and fix. The message is shown in the GUI as-is."""


class AccessDenied(UserError):
    """The signed-in user is not allowed to do this (the attempt has been written to the audit log)."""


class DatabaseUnavailable(UserError):
    """The MySQL server cannot be reached."""


_CONNECTION_ERRORS = {2002, 2003, 2006, 2013, 2055, 1045, 1049, 1130, 1044}


def friendly_message(exc: Exception) -> str:
    """Turn any exception into a safe message: no SQL, no credentials, no stack traces."""
    if isinstance(exc, UserError):
        return str(exc)
    if isinstance(exc, mysql.connector.Error):
        code = getattr(exc, "errno", None)
        if code in _CONNECTION_ERRORS or isinstance(exc, mysql.connector.errors.InterfaceError):
            return ("The database is not reachable. Check that MySQL is running and that the "
                    "settings in the .env file are correct.")
        if code == 1644:  # SIGNAL raised by one of our triggers: the message was written by us
            return getattr(exc, "msg", None) or "The change violates a business rule."
        if code == errorcode.ER_DUP_ENTRY:
            return "This record already exists (a value that must be unique is already used)."
        if code in (errorcode.ER_NO_REFERENCED_ROW_2, errorcode.ER_NO_REFERENCED_ROW):
            return "A selected value no longer exists. Please refresh the page and choose again."
        if code in (errorcode.ER_ROW_IS_REFERENCED_2, errorcode.ER_ROW_IS_REFERENCED):
            return "This record is used elsewhere and cannot be removed. Deactivate it instead."
        if code in (3819, 4025):
            return "One of the values is outside the allowed range or not allowed by a database rule."
        if code in (1264, 1265, 1366, 1292, 1406):
            return "One of the values is invalid or too large."
        if code in (1205, 1213):
            return "The system is busy with another change. Please try again in a moment."
    log.exception("Unexpected error", exc_info=exc)
    return "Something went wrong and the operation was not completed. Nothing was changed."
