from flask import jsonify
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from werkzeug.exceptions import HTTPException

from .extensions import db


class ApiError(Exception):
    def __init__(self, message, status=400, details=None):
        self.message, self.status, self.details = message, status, details


def ok(data=None, status=200, **extra):
    return jsonify({"success": True, "data": data, **extra}), status


def fail(message, status=400, details=None):
    return jsonify({"success": False, "error": {"message": message, "details": details}}), status


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api(e):
        db.session.rollback()  # discard any attribute changes made before the error was raised
        return fail(e.message, e.status, e.details)

    @app.errorhandler(IntegrityError)
    def _integrity(e):
        db.session.rollback()
        return fail("Database constraint violated", 409, str(e.orig))

    @app.errorhandler(OperationalError)
    def _unavailable(e):
        db.session.rollback()
        app.logger.error("database unavailable: %s", type(e.orig).__name__ if e.orig else "OperationalError")
        return fail("Database temporarily unavailable. Please retry shortly.", 503)

    @app.errorhandler(SQLAlchemyError)
    def _db(e):
        db.session.rollback()
        app.logger.exception("database error")
        return fail("Database error", 500)

    @app.errorhandler(HTTPException)
    def _http(e):
        return fail(e.description, e.code)

    @app.errorhandler(Exception)
    def _any(e):
        app.logger.exception("unhandled error")
        return fail("Internal server error", 500)
