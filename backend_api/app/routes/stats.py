from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import StatsQuerySchema, StatsSchema, ErrorSchema
from app.services.session_service import session_service

blp = Blueprint(
    "Stats",
    "stats",
    url_prefix="/stats",
    description="Fetch session statistics",
)


@blp.route("", methods=["GET"])
class StatsAPI(MethodView):
    """
    PUBLIC_INTERFACE
    Endpoint to fetch statistics for a session.

    Provide session_id as query parameter.
    """

    @blp.arguments(StatsQuerySchema, location="query")
    @blp.response(200, StatsSchema)
    @blp.alt_response(404, schema=ErrorSchema, description="Session or stats not found yet")
    def get(self, query_args):
        """Get stats for a given session_id."""
        session_id = query_args["session_id"]
        stats = session_service.get_stats(session_id)
        if not stats:
            blp.abort(404, message="Stats not available yet or session not found")
        return stats
