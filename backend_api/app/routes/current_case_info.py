from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import SessionQuerySchema, CurrentCaseInfoResponseSchema, ErrorSchema
from app.services.session_service import session_service

blp = Blueprint(
    "CurrentCaseInfo",
    "current_case_info",
    url_prefix="/current_case_info",
    description="Get current running case info for a session",
)


@blp.route("", methods=["GET"])
class CurrentCaseInfoAPI(MethodView):
    """
    PUBLIC_INTERFACE
    Get current test case info for a session.

    Query parameters:
      - session_id: the session identifier

    Returns current case name and documentation if available.
    """

    @blp.arguments(SessionQuerySchema, location="query")
    @blp.response(200, CurrentCaseInfoResponseSchema)
    @blp.alt_response(404, schema=ErrorSchema, description="Session not found")
    def get(self, query_args):
        """Return current case info for session."""
        sid = query_args["session_id"]
        data = session_service.get_current_case_info(sid)
        if data is None:
            blp.abort(404, message="Session not found")
        return data
