from __future__ import annotations

from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """
    PUBLIC_INTERFACE
    Register JSON error handlers for common HTTP errors and default exceptions.
    """
    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        response = {
            "code": e.code or 500,
            "status": e.name or "Internal Server Error",
            "message": e.description or "An unexpected error has occurred.",
            "errors": {},
        }
        return jsonify(response), e.code or 500

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e: Exception):
        response = {
            "code": 500,
            "status": "Internal Server Error",
            "message": str(e),
            "errors": {},
        }
        return jsonify(response), 500
