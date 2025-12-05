from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import SessionQuerySchema, UILockResponseSchema, ErrorSchema
from app.services.session_service import session_service

blp = Blueprint(
    "UILock",
    "ui_lock",
    url_prefix="/ui_lock",
    description="Get UI lock state for a session",
)


@blp.route("", methods=["GET"])
class UILockAPI(MethodView):
    """
    PUBLIC_INTERFACE
    Get UI lock state for a session.

    Query parameters:
      - session_id: the session identifier

    Returns whether UI should be locked.
    """

    @blp.arguments(SessionQuerySchema, location="query")
    @blp.response(200, UILockResponseSchema)
    @blp.alt_response(404, schema=ErrorSchema, description="Session not found")
    def get(self, query_args):
        """Return UI lock state for the session."""
        sid = query_args["session_id"]
        data = session_service.get_ui_lock(sid)
        if not data:
            blp.abort(404, message="Session not found")
        return data
