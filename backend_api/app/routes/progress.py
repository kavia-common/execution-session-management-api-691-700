from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import ProgressQuerySchema, ProgressSchema, ErrorSchema
from app.services.session_service import session_service

blp = Blueprint(
    "Progress",
    "progress",
    url_prefix="/progress",
    description="Track session progress",
)


@blp.route("", methods=["GET"])
class ProgressAPI(MethodView):
    """
    PUBLIC_INTERFACE
    Endpoint to fetch progress for a session.

    Provide session_id as query parameter.
    """

    @blp.arguments(ProgressQuerySchema, location="query")
    @blp.response(200, ProgressSchema)
    @blp.alt_response(404, schema=ErrorSchema, description="Session not found")
    def get(self, query_args):
        """Get progress for a given session_id."""
        session_id = query_args["session_id"]
        progress = session_service.get_progress(session_id)
        if not progress:
            blp.abort(404, message="Session not found")
        return {
            "total_steps": progress.total_steps,
            "current_step": progress.current_step,
            "percent": progress.percent,
        }
