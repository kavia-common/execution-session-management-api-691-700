from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import LogsQuerySchema, LogEntrySchema, ErrorSchema
from app.services.session_service import session_service

blp = Blueprint(
    "Logs",
    "logs",
    url_prefix="/logs",
    description="Retrieve session logs",
)


@blp.route("", methods=["GET"])
class LogsAPI(MethodView):
    """
    PUBLIC_INTERFACE
    Endpoint to fetch logs for a session.

    Provide session_id as query parameter; optional level and limit are supported.
    """

    @blp.arguments(LogsQuerySchema, location="query")
    @blp.response(200, LogEntrySchema(many=True))
    @blp.alt_response(404, schema=ErrorSchema, description="Session not found")
    def get(self, query_args):
        """Get logs for a given session_id with optional filters."""
        session_id = query_args["session_id"]
        level = query_args.get("level")
        limit = query_args.get("limit")
        logs = session_service.get_logs(session_id, level=level, limit=limit)
        if logs is None:
            blp.abort(404, message="Session not found")
        return logs
