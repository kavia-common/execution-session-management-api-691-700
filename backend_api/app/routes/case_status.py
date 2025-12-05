from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import SessionQuerySchema, CaseStatusResponseSchema, ErrorSchema
from app.services.session_service import session_service

blp = Blueprint(
    "CaseStatus",
    "case_status",
    url_prefix="/case_status",
    description="Get per-case statuses for a session",
)


@blp.route("", methods=["GET"])
class CaseStatusAPI(MethodView):
    """
    PUBLIC_INTERFACE
    Get per-case statuses (NOTRUN, SCHEDULE, TESTING, PASS, FAIL, SKIP) for a session.

    Query parameters:
      - session_id: the session identifier

    Returns a list of cases with their statuses.
    """

    @blp.arguments(SessionQuerySchema, location="query")
    @blp.response(200, CaseStatusResponseSchema)
    @blp.alt_response(404, schema=ErrorSchema, description="Session not found")
    def get(self, query_args):
        """Return per-case statuses for the session."""
        sid = query_args["session_id"]
        data = session_service.get_case_status(sid)
        if not data:
            blp.abort(404, message="Session not found")
        return data
