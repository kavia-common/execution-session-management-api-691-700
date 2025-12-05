from __future__ import annotations

from flask.views import MethodView
from flask_smorest import Blueprint

from app.schemas import RunRequestSchema, RunResponseSchema, ErrorSchema
from app.services.session_service import session_service

blp = Blueprint(
    "Run",
    "run",
    url_prefix="/run",
    description="Start execution sessions",
)


@blp.route("", methods=["POST"])
class RunAPI(MethodView):
    """
    PUBLIC_INTERFACE
    Endpoint to start a new execution session.

    Returns the created session id and initial status.
    """

    @blp.arguments(RunRequestSchema, location="json")
    @blp.response(201, RunResponseSchema)
    @blp.alt_response(400, schema=ErrorSchema, description="Bad request")
    @blp.alt_response(500, schema=ErrorSchema, description="Server error")
    def post(self, body):
        """Start a run with the provided payload."""
        session = session_service.create_session(body or {})
        return {
            "session_id": session.session_id,
            "status": session.status,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }
